"""
Announcement models.
"""

from django.db import models
from django.conf import settings


class Announcement(models.Model):
    """
    Church announcements.
    """
    
    # Content
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    # Type
    type = models.CharField(
        max_length=50,
        choices=[
            ('general', 'General'),
            ('urgent', 'Urgent'),
            ('celebration', 'Celebration'),
            ('cancellation', 'Cancellation'),
            ('schedule_change', 'Schedule Change'),
            ('other', 'Other'),
        ],
        default='general'
    )
    
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
    
    # Target Audience
    target_audience = models.CharField(
        max_length=50,
        choices=[
            ('all', 'All Members'),
            ('members', 'Members Only'),
            ('youth', 'Youth'),
            ('children', 'Children'),
            ('leaders', 'Leaders'),
            ('specific', 'Specific Group'),
        ],
        default='all'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_urgent = models.BooleanField(default=False)
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'announcements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_expired(self):
        """Check if announcement is expired."""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False
