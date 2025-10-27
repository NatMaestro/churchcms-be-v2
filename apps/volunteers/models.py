"""
Volunteer opportunity models.
"""

from django.db import models
from django.conf import settings
from decimal import Decimal


class VolunteerOpportunity(models.Model):
    """
    Volunteer opportunities.
    """
    
    # Basic Information
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Category
    category = models.CharField(
        max_length=50,
        choices=[
            ('ministry', 'Ministry'),
            ('event', 'Event'),
            ('community', 'Community'),
            ('administration', 'Administration'),
            ('other', 'Other'),
        ]
    )
    
    # Ministry Link (optional)
    ministry = models.ForeignKey(
        'ministries.Ministry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='volunteer_opportunities'
    )
    
    # Location & Schedule
    location = models.CharField(max_length=255)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    schedule = models.CharField(
        max_length=20,
        choices=[
            ('one_time', 'One Time'),
            ('recurring', 'Recurring'),
            ('flexible', 'Flexible'),
        ],
        default='one_time'
    )
    
    recurrence_pattern = models.CharField(max_length=20, blank=True)
    
    # Capacity
    spots_available = models.IntegerField(null=True, blank=True)
    spots_filled = models.IntegerField(default=0)
    
    # Requirements
    requirements = models.TextField(blank=True)
    hours_per_week = models.IntegerField(null=True, blank=True)
    
    commitment = models.CharField(
        max_length=20,
        choices=[
            ('short_term', 'Short Term'),
            ('long_term', 'Long Term'),
            ('ongoing', 'Ongoing'),
        ],
        blank=True
    )
    
    # Contact
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_urgent = models.BooleanField(default=False)
    
    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_opportunities'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'volunteer_opportunities'
        ordering = ['-created_at']
        verbose_name_plural = 'Volunteer opportunities'
    
    def __str__(self):
        return self.title
    
    @property
    def is_full(self):
        """Check if all spots are filled."""
        if self.spots_available:
            return self.spots_filled >= self.spots_available
        return False


class VolunteerSignup(models.Model):
    """
    Volunteer signups for opportunities.
    """
    
    opportunity = models.ForeignKey(
        VolunteerOpportunity,
        on_delete=models.CASCADE,
        related_name='signups'
    )
    
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='volunteer_signups'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='volunteer_signups'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )
    
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_signups'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Completion
    hours_completed = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    completed_date = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    # Timestamps
    signup_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'volunteer_signups'
        unique_together = ['opportunity', 'member']
        ordering = ['-signup_date']
    
    def __str__(self):
        return f"{self.member.full_name} - {self.opportunity.title}"


class VolunteerHours(models.Model):
    """
    Track volunteer hours.
    """
    
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='volunteer_hours'
    )
    
    opportunity = models.ForeignKey(
        VolunteerOpportunity,
        on_delete=models.CASCADE,
        related_name='logged_hours'
    )
    
    signup = models.ForeignKey(
        VolunteerSignup,
        on_delete=models.CASCADE,
        related_name='logged_hours',
        null=True,
        blank=True
    )
    
    # Hours
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    
    # Verification
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_hours'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'volunteer_hours'
        ordering = ['-date']
        verbose_name_plural = 'Volunteer hours'
    
    def __str__(self):
        return f"{self.member.full_name} - {self.hours} hours on {self.date}"
