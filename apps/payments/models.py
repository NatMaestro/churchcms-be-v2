"""
Payment and giving models.
Comprehensive financial tracking with tax receipts.
"""

from django.db import models
from django.conf import settings
from decimal import Decimal


class Payment(models.Model):
    """
    Payment/donation model.
    """
    
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='payments')
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GHS')
    
    type = models.CharField(
        max_length=50,
        choices=[
            ('tithe', 'Tithe'),
            ('offering', 'Offering'),
            ('pledge', 'Pledge'),
            ('donation', 'Donation'),
            ('building_fund', 'Building Fund'),
            ('mission', 'Mission'),
            ('special', 'Special Offering'),
            ('other', 'Other'),
        ]
    )
    
    method = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'Cash'),
            ('check', 'Check'),
            ('online', 'Online'),
            ('bank_transfer', 'Bank Transfer'),
            ('mobile_money', 'Mobile Money'),
        ],
        default='cash'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='completed'
    )
    
    # Reference & Notes
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    notes = models.TextField(blank=True)
    
    # Date
    date = models.DateTimeField(db_index=True)
    
    # Pledges
    pledge_id = models.CharField(max_length=100, blank=True)
    is_recurring = models.BooleanField(default=False)
    recurring_frequency = models.CharField(max_length=20, blank=True)
    recurring_end_date = models.DateField(null=True, blank=True)
    
    # Tax Information
    fiscal_year = models.IntegerField(null=True, blank=True)
    receipt_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    is_tax_deductible = models.BooleanField(default=True)
    receipt_issued = models.BooleanField(default=False)
    receipt_issued_at = models.DateTimeField(null=True, blank=True)
    
    # Category
    category = models.CharField(max_length=100, blank=True)
    subcategory = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['member', 'date']),
            models.Index(fields=['fiscal_year']),
            models.Index(fields=['type']),
            models.Index(fields=['reference']),
        ]
    
    def __str__(self):
        return f"{self.member.full_name} - {self.type} - {self.amount}"


class Pledge(models.Model):
    """
    Member pledges.
    """
    
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='pledges')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ]
    )
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='active'
    )
    
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pledges'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.member.full_name} - {self.amount} ({self.frequency})"
    
    @property
    def amount_remaining(self):
        """Calculate remaining pledge amount."""
        return self.amount - self.amount_paid


class TaxReceipt(models.Model):
    """
    Annual tax receipts for charitable donations.
    """
    
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='tax_receipts')
    
    fiscal_year = models.IntegerField(db_index=True)
    receipt_number = models.CharField(max_length=100, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_ids = models.JSONField(default=list)  # Array of payment IDs included
    
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_receipts'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    
    pdf_path = models.CharField(max_length=500, blank=True)
    
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tax_receipts'
        unique_together = ['member', 'fiscal_year']
        ordering = ['-fiscal_year']
    
    def __str__(self):
        return f"{self.receipt_number} - {self.member.full_name} ({self.fiscal_year})"
