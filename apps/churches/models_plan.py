"""
Subscription plans, edited by platform admins and shown on the landing page.

A plan's price can change at any time. Payments keep their own copy of the
amount actually charged (SubscriptionPayment.amount), so editing a price only
affects future payments, never history.
"""
from django.db import models

PLAN_CURRENCY = 'GHS'


class Plan(models.Model):
    code = models.SlugField(
        max_length=20, unique=True,
        help_text='Stable identifier stored on churches and payments, e.g. "standard". Never rename.',
    )
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=200, blank=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Leave empty if the plan cannot be paid yearly.',
    )
    member_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text='Empty means unlimited members.',
    )
    features = models.JSONField(
        default=list, blank=True, help_text='Bullet points shown with the plan.',
    )
    is_active = models.BooleanField(
        default=True, help_text='Inactive plans cannot be bought or renewed.',
    )
    is_public = models.BooleanField(
        default=True, help_text='Shown on the landing page.',
    )
    is_featured = models.BooleanField(default=False, help_text='Highlighted as the recommended plan.')
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'plans'
        ordering = ['sort_order', 'price_monthly']

    def __str__(self):
        return self.name

    def price_for(self, duration):
        """Price for 'monthly' or 'yearly', or None if this plan has no such price."""
        if duration == 'monthly':
            return self.price_monthly
        if duration == 'yearly':
            return self.price_yearly
        return None
