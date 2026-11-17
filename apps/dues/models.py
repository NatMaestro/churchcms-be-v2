"""
Church dues: the digital side of a parish dues card.

A church sets up a dues plan for a year (paid monthly or yearly) with
categories that each have their own amount and, optionally, an age range
used to place members automatically. Staff can move a member to another
category or mark them exempt. Dues payments are recorded by the church
office and kept separate from giving; a payment recorded by mistake is
reversed with a reason, never edited or deleted.

Field classification: PERSONAL = identifies a person (member link);
FINANCIAL = an amount owed or paid; INTERNAL = written by staff.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MONTHLY = 'monthly'
YEARLY = 'yearly'
FREQUENCIES = [(MONTHLY, 'Monthly'), (YEARLY, 'Yearly')]

PAYMENT_METHODS = [
    ('cash', 'Cash'),
    ('mobile_money', 'Mobile Money'),
    ('bank_transfer', 'Bank transfer'),
    ('check', 'Cheque'),
]


class DuesPlan(models.Model):
    """Dues for one year, e.g. "Parish dues 2027", paid monthly or yearly."""

    name = models.CharField(max_length=150)
    year = models.PositiveIntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    frequency = models.CharField(max_length=10, choices=FREQUENCIES, default=MONTHLY)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dues_plans'
        ordering = ['-year', 'name']
        constraints = [models.UniqueConstraint(fields=['year', 'name'], name='unique_dues_plan_per_year')]

    def __str__(self):
        return f'{self.name} ({self.year})'


class DuesCategory(models.Model):
    """
    A group within a plan with its own amount (per month for monthly plans,
    per year for yearly plans). Members whose age on 1 January of the plan
    year falls in [min_age, max_age] are placed here automatically.
    """

    plan = models.ForeignKey(DuesPlan, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2,
                                 validators=[MinValueValidator(Decimal('0.01'))])  # FINANCIAL, GH₵
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'dues_categories'
        ordering = ['sort_order', 'name']
        constraints = [models.UniqueConstraint(fields=['plan', 'name'], name='unique_dues_category_name')]

    def __str__(self):
        return f'{self.name} ({self.plan})'

    def fits_age(self, age):
        if self.min_age is None and self.max_age is None:
            return False  # no age range: only assigned by hand
        if age is None:
            return False
        return (self.min_age is None or age >= self.min_age) and (self.max_age is None or age <= self.max_age)


class DuesAssignment(models.Model):
    """A staff decision for one member in one plan: a specific category, or exempt."""

    plan = models.ForeignKey(DuesPlan, on_delete=models.CASCADE, related_name='assignments')
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='dues_assignments')  # PERSONAL
    category = models.ForeignKey(DuesCategory, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='assignments')
    is_exempt = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)  # INTERNAL
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dues_assignments'
        constraints = [models.UniqueConstraint(fields=['plan', 'member'], name='unique_dues_assignment')]


class DuesPayment(models.Model):
    """
    A dues payment recorded by the church office. For a monthly plan it
    covers the listed months (1-12); for a yearly plan it counts toward the
    year's balance. Status "reversed" keeps a mistaken entry in the history.
    """

    COMPLETED = 'completed'
    REVERSED = 'reversed'

    plan = models.ForeignKey(DuesPlan, on_delete=models.PROTECT, related_name='payments')
    member = models.ForeignKey('members.Member', on_delete=models.PROTECT, related_name='dues_payments')  # PERSONAL
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # FINANCIAL, GH₵
    months = models.JSONField(default=list, blank=True)  # monthly plans: e.g. [1, 2, 3]
    date = models.DateField()
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    reference = models.CharField(max_length=100, unique=True)  # receipt / booklet number
    status = models.CharField(max_length=10, choices=[(COMPLETED, 'Completed'), (REVERSED, 'Reversed')],
                              default=COMPLETED)
    notes = models.TextField(blank=True)  # INTERNAL
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dues_payments'
        ordering = ['-date', '-created_at']
        indexes = [models.Index(fields=['plan', 'member', 'status'])]

    def __str__(self):
        return f'{self.reference}: {self.amount} ({self.plan})'
