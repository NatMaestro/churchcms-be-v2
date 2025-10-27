"""
Notification models.
System notifications for users.
"""

from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    User notifications.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification Content
    type = models.CharField(
        max_length=50,
        choices=[
            ('system', 'System'),
            ('event', 'Event'),
            ('payment', 'Payment'),
            ('request', 'Request'),
            ('ministry', 'Ministry'),
            ('announcement', 'Announcement'),
            ('volunteer', 'Volunteer'),
            ('prayer', 'Prayer'),
            ('altar_call', 'Altar Call'),
            ('member_request', 'Member Request'),
            ('admin_message', 'Admin Message'),
            ('event_reminder', 'Event Reminder'),
            ('other', 'Other'),
        ]
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Priority
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='normal'
    )
    
    # Category
    category = models.CharField(max_length=50, blank=True)
    
    # Action
    action_type = models.CharField(
        max_length=50,
        choices=[
            ('info', 'Information'),
            ('action_required', 'Action Required'),
            ('reminder', 'Reminder'),
            ('alert', 'Alert'),
        ],
        default='info'
    )
    
    action_url = models.CharField(max_length=500, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    data = models.JSONField(default=dict, blank=True)  # Alias for compatibility
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    # Expiry
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.name} - {self.title}"


class NotificationPreference(models.Model):
    """
    User notification preferences.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    channel = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('sms', 'SMS'),
            ('push', 'Push'),
            ('in_app', 'In-App'),
        ]
    )
    
    category = models.CharField(max_length=50)
    
    enabled = models.BooleanField(default=True)
    
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='immediate'
    )
    
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        unique_together = ['user', 'channel', 'category']
    
    def __str__(self):
        return f"{self.user.name} - {self.channel} - {self.category}"
