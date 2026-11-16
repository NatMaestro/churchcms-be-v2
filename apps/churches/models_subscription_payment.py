"""
Subscription payment models for Paystack integration.
Stores subscription payment transactions.
"""

from django.db import models
from django.utils import timezone
from decimal import Decimal


class SubscriptionPayment(models.Model):
    """
    Subscription payment transaction model.
    Stores payment records for church subscriptions.
    """
    
    church = models.ForeignKey('churches.Church', on_delete=models.CASCADE, related_name='subscription_payments')
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GHS')
    
    # Plan Information
    # A Plan.code. Plans live in the database, so this is not a fixed choice list.
    plan = models.CharField(max_length=20)
    duration = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly'
    )
    
    # Paystack Details
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    paystack_reference = models.CharField(max_length=100, blank=True, db_index=True)
    authorization_url = models.URLField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )
    
    # Paystack Response (for audit)
    paystack_response = models.JSONField(default=dict, blank=True)
    
    # Subscription Activation
    subscription_activated = models.BooleanField(default=False)
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    
    # How the money arrived. Paystack payments are recorded automatically;
    # the rest are recorded by a platform admin.
    payment_method = models.CharField(
        max_length=20, default='paystack',
        choices=[
            ('paystack', 'Paystack'),
            ('mobile_money', 'Mobile Money'),
            ('bank_transfer', 'Bank transfer'),
            ('cash', 'Cash'),
            ('other', 'Other'),
        ],
    )
    recorded_by = models.ForeignKey(
        'authentication.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='recorded_subscription_payments',
    )
    note = models.TextField(blank=True)

    # User Information (who initiated payment)
    user_email = models.EmailField()
    user_name = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'subscription_payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['church', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.church.name} - {self.plan} - {self.amount} {self.currency} ({self.status})"
    
    def mark_completed(self):
        """Mark payment as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
    
    def activate_subscription(self):
        """Give the church this payment's paid period (idempotent)."""
        from .subscriptions import activate_paid_period

        activate_paid_period(self.pk)
        self.refresh_from_db()
