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
