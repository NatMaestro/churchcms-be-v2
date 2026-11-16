"""
Subscription rules in one place: trials, paid periods and payment checks.

Every way of paying (Paystack redirect, Paystack webhook, a payment a platform
admin records by hand) ends in `activate_paid_period`, so they all extend a
church's subscription the same way and can never apply the same payment twice.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

TRIAL_PLAN = 'trial'
TRIAL_DAYS = 30
PERIOD_DAYS = {'monthly': 30, 'yearly': 365}
MINOR_UNITS_PER_MAJOR = 100  # pesewas per cedi
CENT = Decimal('0.01')


def to_minor_units(amount):
    """GHS amount -> integer pesewas, as Paystack expects. The only rounding rule."""
    return int((Decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)) * MINOR_UNITS_PER_MAJOR)


def start_trial(church, now=None):
    """Put `church` on a fresh trial. Callers decide whether a trial is allowed."""
    now = now or timezone.now()
    church.plan = TRIAL_PLAN
    church.subscription_status = 'active'
    church.trial_started_at = now
    church.trial_end_date = now + timedelta(days=TRIAL_DAYS)


def charge_matches_payment(payment, charge):
    """True if a Paystack charge paid exactly what `payment` asked for."""
    return (
        charge.get('amount') == to_minor_units(payment.amount)
        and str(charge.get('currency', '')).upper() == payment.currency.upper()
    )


def activate_paid_period(payment_id, gateway_response=None):
    """
    Mark a payment completed and give its church the paid period. Idempotent.

    The period starts when the church's current paid period ends (so paying
    early never loses days), or now if it has none or it already ended.
    Both rows are locked, so a redirect and a webhook arriving together
    cannot apply the same payment twice.
    """
    from .models import Church
    from .models_subscription_payment import SubscriptionPayment

    with transaction.atomic():
        payment = SubscriptionPayment.objects.select_for_update().get(pk=payment_id)
        if payment.subscription_activated:
            return payment
        church = Church.objects.select_for_update().get(pk=payment.church_id)

        now = timezone.now()
        current_end = church.subscription_end_date
        extends_current = current_end is not None and current_end > now
        period_start = current_end if extends_current else now
        period_end = period_start + timedelta(days=PERIOD_DAYS[payment.duration])

        church.plan = payment.plan
        church.subscription_status = 'active'
        if not extends_current:
            church.subscription_start_date = now
        church.subscription_end_date = period_end
        church.trial_end_date = None
        church.save(update_fields=['plan', 'subscription_status', 'subscription_start_date',
                                   'subscription_end_date', 'trial_end_date', 'updated_at'])

        payment.status = 'completed'
        payment.completed_at = payment.completed_at or now
        payment.subscription_activated = True
        payment.subscription_start_date = period_start
        payment.subscription_end_date = period_end
        fields = ['status', 'completed_at', 'subscription_activated',
                  'subscription_start_date', 'subscription_end_date', 'updated_at']
        if gateway_response is not None:
            payment.paystack_response = gateway_response
            fields.append('paystack_response')
        payment.save(update_fields=fields)
        return payment


# --- Platform admin actions -------------------------------------------------

MANUAL_PAYMENT_METHODS = ('mobile_money', 'bank_transfer', 'cash', 'other')
MAX_TRIAL_EXTENSION_DAYS = 90


class SubscriptionActionError(ValueError):
    """A platform admin action that cannot be applied (shown to the admin as-is)."""


class PaymentReferenceConflict(SubscriptionActionError):
    """The payment reference already belongs to another church."""


def record_manual_payment(church, *, plan_code, duration, reference, method, actor,
                          amount=None, note=''):
    """
    Record a payment received outside Paystack (Mobile Money, bank transfer, ...)
    and give the church its paid period.

    Idempotent on `reference`: recording the same reference again for the same
    church returns the existing payment and adds no time.
    """
    from .models_plan import PLAN_CURRENCY, Plan
    from .models_subscription_payment import SubscriptionPayment

    if duration not in PERIOD_DAYS:
        raise SubscriptionActionError('Duration must be monthly or yearly.')
    if method not in MANUAL_PAYMENT_METHODS:
        raise SubscriptionActionError('Unknown payment method.')
    reference = (reference or '').strip()
    if not reference:
        raise SubscriptionActionError('A payment reference is required.')

    existing = SubscriptionPayment.objects.filter(reference=reference).first()
    if existing is not None:
        if existing.church_id != church.pk:
            raise PaymentReferenceConflict('This reference is already recorded for another church.')
        return activate_paid_period(existing.pk), False

    plan = Plan.objects.filter(code=plan_code).first()
    if plan is None:
        raise SubscriptionActionError('Unknown plan.')
    if amount is None:
        amount = plan.price_for(duration)
    if amount is None or Decimal(amount) <= 0:
        raise SubscriptionActionError('Enter the amount received.')

    payment = SubscriptionPayment.objects.create(
        church=church, amount=Decimal(amount), currency=PLAN_CURRENCY, plan=plan.code,
        duration=duration, reference=reference, status='processing',
        payment_method=method, recorded_by=actor, note=note or '',
        user_email=actor.email, user_name=actor.name,
    )
    return activate_paid_period(payment.pk), True


def extend_trial(church, days, now=None):
    """Add `days` to a church's trial (from today if it already ended)."""
    if church.plan != TRIAL_PLAN:
        raise SubscriptionActionError('This church is on a paid plan; record a payment instead.')
    if not 1 <= days <= MAX_TRIAL_EXTENSION_DAYS:
        raise SubscriptionActionError(f'Extend by 1 to {MAX_TRIAL_EXTENSION_DAYS} days.')
    now = now or timezone.now()
    if church.trial_started_at is None:
        church.trial_started_at = now
    base = church.trial_end_date if church.trial_end_date and church.trial_end_date > now else now
    church.trial_end_date = base + timedelta(days=days)
    church.save(update_fields=['trial_started_at', 'trial_end_date', 'updated_at'])
    return church


def set_suspended(church, suspended):
    church.subscription_status = 'suspended' if suspended else 'active'
    church.save(update_fields=['subscription_status', 'updated_at'])
    return church


def set_free_access(church, enabled):
    """Free churches (like the pilot) are never blocked for subscription reasons."""
    church.bypass_subscription_check = bool(enabled)
    church.save(update_fields=['bypass_subscription_check', 'updated_at'])
    return church


def account_state(church, now=None):
    """One plain label per church for the platform admin list."""
    now = now or timezone.now()
    if church.subscription_status in ('suspended', 'cancelled'):
        return church.subscription_status
    if church.bypass_subscription_check:
        return 'free'
    if church.plan == TRIAL_PLAN:
        return 'trial_ended' if church.trial_end_date and church.trial_end_date <= now else 'trial'
    if church.subscription_end_date and church.subscription_end_date > now:
        return 'paying'
    return 'lapsed'


def account_state_filter(state, now=None):
    """Database filter matching `account_state` labels, so lists stay paginated."""
    from django.db.models import Q

    now = now or timezone.now()
    not_blocked = ~Q(subscription_status__in=['suspended', 'cancelled'])
    open_ = not_blocked & Q(bypass_subscription_check=False)
    filters = {
        'suspended': Q(subscription_status__in=['suspended', 'cancelled']),
        'free': not_blocked & Q(bypass_subscription_check=True),
        'trial': open_ & Q(plan=TRIAL_PLAN) & (Q(trial_end_date__isnull=True) | Q(trial_end_date__gt=now)),
        'trial_ended': open_ & Q(plan=TRIAL_PLAN, trial_end_date__lte=now),
        'paying': open_ & ~Q(plan=TRIAL_PLAN) & Q(subscription_end_date__gt=now),
        'lapsed': open_ & ~Q(plan=TRIAL_PLAN) & (Q(subscription_end_date__isnull=True)
                                                  | Q(subscription_end_date__lte=now)),
    }
    return filters.get(state)
