"""
Altar call models.
For Pentecostal and non-denominational churches.
"""

from django.db import models
from django.conf import settings


class AltarCall(models.Model):
    """
    Altar call records for salvation, healing, rededication, etc.
    """
    
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='altar_calls',
        null=True,
        blank=True
    )
    
    # Service Information
    service_date = models.DateField()
    service_type = models.CharField(
        max_length=100,
        choices=[
            ('sunday_service', 'Sunday Service'),
            ('midweek_service', 'Midweek Service'),
            ('special_event', 'Special Event'),
            ('revival', 'Revival'),
            ('crusade', 'Crusade'),
            ('other', 'Other'),
        ]
    )
    
    # Decision/Reason
    reason = models.CharField(
        max_length=50,
        choices=[
            ('salvation', 'Salvation'),
            ('rededication', 'Rededication'),
            ('healing', 'Healing'),
            ('baptism', 'Baptism'),
            ('deliverance', 'Deliverance'),
            ('ministry', 'Ministry Call'),
            ('other', 'Other'),
        ]
    )
    
    # Details
    notes = models.TextField(blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=True)
    follow_up_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('not_applicable', 'Not Applicable'),
        ],
        default='pending'
    )
    follow_up_notes = models.TextField(blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_altar_calls'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'altar_calls'
        ordering = ['-service_date', '-created_at']
        indexes = [
            models.Index(fields=['service_date']),
            models.Index(fields=['reason']),
            models.Index(fields=['follow_up_status']),
        ]
    
    def __str__(self):
        member_name = self.member.full_name if self.member else 'Guest'
        return f"{member_name} - {self.reason} on {self.service_date}"
