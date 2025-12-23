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
    plan = models.CharField(
        max_length=20,
        choices=[
            ('basic', 'Basic'),
            ('standard', 'Standard'),
            ('premium', 'Premium'),
            ('enterprise', 'Enterprise'),
        ]
    )
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
        """Activate subscription after successful payment."""
        from django.utils import timezone
        from datetime import timedelta
        
        if self.subscription_activated:
            return
        
        now = timezone.now()
        if self.duration == 'yearly':
            subscription_end = now + timedelta(days=365)
        else:
            subscription_end = now + timedelta(days=30)
        
        # Update church subscription
        self.church.plan = self.plan
        self.church.subscription_status = 'active'
        self.church.subscription_start_date = now
        self.church.subscription_end_date = subscription_end
        self.church.trial_end_date = None  # Clear trial if upgrading
        self.church.save(update_fields=['plan', 'subscription_status', 'subscription_start_date', 'subscription_end_date', 'trial_end_date'])
        
        # Update payment record
        self.subscription_activated = True
        self.subscription_start_date = now
        self.subscription_end_date = subscription_end
        self.save(update_fields=['subscription_activated', 'subscription_start_date', 'subscription_end_date', 'updated_at'])


