"""
Dues rules in one place: which category applies to a member, what their
card shows, what a payment must look like, and who is behind.

Amounts are GH₵ Decimals with 2 places; nothing here uses floats.
"""
import uuid
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.members.models import Member

from .models import MONTHLY, DuesAssignment, DuesCategory, DuesPayment, DuesPlan

ALL_MONTHS = list(range(1, 13))


class DuesError(ValueError):
    """A dues action that can't be done as asked (message is shown to staff as-is)."""


def age_on(birth_date, on_date):
    """Whole years old on `on_date`, or None without a birth date."""
    if not birth_date:
        return None
    return on_date.year - birth_date.year - ((on_date.month, on_date.day) < (birth_date.month, birth_date.day))


def resolve_category(member, plan, categories, assignment):
    """
    (category or None, how): how = 'exempt' | 'assigned' | 'by_age' | 'unassigned'.
    A staff assignment wins; otherwise the member's age on 1 January of the plan year.
    """
    if assignment is not None:
        if assignment.is_exempt:
            return None, 'exempt'
        if assignment.category_id:
            return assignment.category, 'assigned'
    age = age_on(member.date_of_birth, date(plan.year, 1, 1))
    for category in categories:
        if category.fits_age(age):
            return category, 'by_age'
    return None, 'unassigned'


def months_due(plan, today=None):
    """Months of a monthly plan that have started by today (all 12 once the year is over)."""
    today = today or timezone.localdate()
    if plan.year < today.year:
        return ALL_MONTHS
    if plan.year > today.year:
        return []
    return list(range(1, today.month + 1))


def build_card(member, plan, categories, assignment, payments, today=None):
    """Everything a dues card shows, from already-loaded rows (no queries)."""
    category, how = resolve_category(member, plan, categories, assignment)
    completed = [p for p in payments if p.status == DuesPayment.COMPLETED]
    paid_total = sum((p.amount for p in completed), Decimal('0.00'))
    card = {
        'plan': {'id': plan.pk, 'name': plan.name, 'year': plan.year, 'frequency': plan.frequency},
        'member': {'id': member.pk, 'name': member.full_name, 'member_id': member.member_id},
        'category': {'id': category.pk, 'name': category.name, 'amount': category.amount} if category else None,
        'category_source': how,
        'paid_total': paid_total,
        'payments': [
            {'id': p.pk, 'amount': p.amount, 'months': p.months, 'date': p.date, 'method': p.method,
             'reference': p.reference, 'status': p.status}
            for p in payments
        ],
    }
    if category is None:
        card.update({'owes': False, 'arrears': Decimal('0.00')})
        if plan.frequency == MONTHLY:
            card.update({'months': [], 'months_in_arrears': []})
        else:
            card.update({'amount_due': Decimal('0.00'), 'balance': Decimal('0.00')})
        return card

    card['owes'] = True
    if plan.frequency == MONTHLY:
        paid_by_month = {}
        for p in completed:
            for month in p.months:
                paid_by_month[month] = p
        due = months_due(plan, today)
        card['months'] = [
            {'month': m, 'paid': m in paid_by_month, 'due': m in due,
             'date': paid_by_month[m].date if m in paid_by_month else None,
             'reference': paid_by_month[m].reference if m in paid_by_month else ''}
            for m in ALL_MONTHS
        ]
        behind = [m for m in due if m not in paid_by_month]
        card['months_in_arrears'] = behind
        card['arrears'] = category.amount * len(behind)
    else:
        balance = max(category.amount - paid_total, Decimal('0.00'))
        card.update({'amount_due': category.amount, 'balance': balance,
                     'arrears': balance if plan.year < (today or timezone.localdate()).year else Decimal('0.00')})
    return card


def load_card(member, plan, today=None):
    categories = list(plan.categories.all())
    assignment = DuesAssignment.objects.filter(plan=plan, member=member).select_related('category').first()
    payments = list(DuesPayment.objects.filter(plan=plan, member=member))
    return build_card(member, plan, categories, assignment, payments, today)


def all_cards(plan, today=None):
    """A card for every active member, loaded with a fixed number of queries."""
    categories = list(plan.categories.all())
    assignments = {a.member_id: a for a in plan.assignments.select_related('category')}
    payments_by_member = {}
    for payment in plan.payments.all():
        payments_by_member.setdefault(payment.member_id, []).append(payment)
    members = Member.objects.filter(status='active').order_by('last_name', 'first_name')
    return [build_card(m, plan, categories, assignments.get(m.pk), payments_by_member.get(m.pk, []), today)
            for m in members]


def _new_reference():
    return f'DUES-{uuid.uuid4().hex[:12].upper()}'


def record_payment(*, plan, member, amount, months, payment_date, method, reference, notes, recorded_by):
    """
    Record a dues payment after checking it against the member's card.
    Monthly: the amount must equal the category amount times the months
    paid, and none of those months may already be paid. Yearly: the amount
    may not exceed what is still owed.
    """
    with transaction.atomic():
        # Lock this member's rows for the plan so two entries can't pay the same month.
        DuesPlan.objects.select_for_update().get(pk=plan.pk)
        card = load_card(member, plan)
        if not card['owes']:
            reason = 'is exempt from' if card['category_source'] == 'exempt' else 'has no dues category in'
            raise DuesError(f'{member.full_name} {reason} {plan.name}.')
        rate = card['category']['amount']
        if plan.frequency == MONTHLY:
            months = sorted(set(months or []))
            if not months or any(m not in ALL_MONTHS for m in months):
                raise DuesError('Choose the months this payment covers.')
            already = [m for m in months if card['months'][m - 1]['paid']]
            if already:
                raise DuesError(f'Already paid: {", ".join(date(plan.year, m, 1).strftime("%B") for m in already)}.')
            expected = rate * len(months)
            if amount != expected:
                raise DuesError(f'{len(months)} month(s) at GH₵{rate} is GH₵{expected}, not GH₵{amount}.')
        else:
            months = []
            if amount > card['balance']:
                raise DuesError(f'Only GH₵{card["balance"]} is still owed for {plan.year}.')
        return DuesPayment.objects.create(
            plan=plan, member=member, amount=amount, months=months, date=payment_date, method=method,
            reference=reference or _new_reference(), notes=notes, recorded_by=recorded_by,
        )


def reverse_payment(payment, reason, user):
    """Mark a payment recorded by mistake as reversed, keeping it and the reason in the history."""
    reason = (reason or '').strip()
    if not reason:
        raise DuesError('Give a reason for reversing this payment.')
    with transaction.atomic():
        payment = DuesPayment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != DuesPayment.COMPLETED:
            raise DuesError('This payment has already been reversed.')
        note = f'Reversed {timezone.localdate():%Y-%m-%d} by {user.name}: {reason}'
        payment.status = DuesPayment.REVERSED
        payment.notes = chr(10).join(part for part in (payment.notes, note) if part)
        payment.save(update_fields=['status', 'notes'])
    return payment
