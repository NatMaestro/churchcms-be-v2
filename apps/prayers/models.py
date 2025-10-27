"""
Prayer request models.
"""

from django.db import models
from django.conf import settings


class PrayerRequest(models.Model):
    """
    Prayer requests from members and visitors.
    """
    
    # Requester (can be member or anonymous)
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='prayer_requests',
        null=True,
        blank=True
    )
    
    requester_name = models.CharField(max_length=255, blank=True)
    requester_email = models.EmailField(blank=True)
    requester_phone = models.CharField(max_length=50, blank=True)
    
    # Prayer Request Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Category
    category = models.CharField(
        max_length=50,
        choices=[
            ('healing', 'Healing'),
            ('family', 'Family'),
            ('financial', 'Financial'),
            ('spiritual', 'Spiritual'),
            ('guidance', 'Guidance'),
            ('thanksgiving', 'Thanksgiving'),
            ('other', 'Other'),
        ]
    )
    
    # Urgency
    urgency = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='normal'
    )
    
    # Privacy
    is_confidential = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('praying', 'Praying'),
            ('answered', 'Answered'),
            ('completed', 'Completed'),
        ],
        default='active'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_prayers'
    )
    
    # Prayer Team
    prayer_team_members = models.JSONField(default=list, blank=True)
    
    # Answer
    answered_at = models.DateTimeField(null=True, blank=True)
    answer_testimony = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prayer_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['urgency']),
        ]
    
    def __str__(self):
        requester = self.member.full_name if self.member else self.requester_name or 'Anonymous'
        return f"{requester} - {self.title}"
