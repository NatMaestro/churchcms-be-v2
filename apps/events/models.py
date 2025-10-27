"""
Event models.
Event management with recurring events and RSVPs.
"""

from django.db import models
from django.conf import settings


class Event(models.Model):
    """
    Event model with support for recurring events and registration.
    """
    
    # Basic Information
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Date & Time
    date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Location
    location = models.CharField(max_length=255)
    
    # Event Type
    type = models.CharField(
        max_length=50,
        choices=[
            ('service', 'Service'),
            ('study', 'Bible Study'),
            ('youth', 'Youth Event'),
            ('ministry', 'Ministry'),
            ('community', 'Community'),
            ('special', 'Special Event'),
            ('other', 'Other'),
        ],
        default='service'
    )
    
    # Capacity & Registration
    capacity = models.IntegerField(null=True, blank=True)
    requires_registration = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    max_attendees = models.IntegerField(null=True, blank=True)
    registration_form = models.JSONField(default=dict, blank=True)
    
    # Recurring Events
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        blank=True,
        null=True
    )
    recurrence_end_date = models.DateField(null=True, blank=True)
    
    # Attendees (JSON field with member IDs)
    attendees = models.JSONField(default=list, blank=True)
    
    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'events'
        ordering = ['date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['type']),
            models.Index(fields=['is_recurring']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.date.strftime('%Y-%m-%d')}"
    
    @property
    def is_full(self):
        """Check if event is at capacity."""
        if self.max_attendees:
            return len(self.attendees) >= self.max_attendees
        return False


class EventRegistration(models.Model):
    """
    Event registration/RSVP.
    """
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='event_registrations')
    
    registration_data = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('registered', 'Registered'),
            ('attended', 'Attended'),
            ('cancelled', 'Cancelled'),
            ('no_show', 'No Show'),
        ],
        default='registered'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'event_registrations'
        unique_together = ['event', 'member']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.member.full_name} - {self.event.title}"
