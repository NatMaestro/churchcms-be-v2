"""
Service request models.
Baptism, marriage, funeral, counseling requests, etc.
"""

from django.db import models
from django.conf import settings


class ServiceRequest(models.Model):
    """
    Service requests from members.
    """
    
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='service_requests'
    )
    
    # Request Type
    type = models.CharField(
        max_length=50,
        choices=[
            ('baptism', 'Baptism'),
            ('marriage', 'Marriage'),
            ('funeral', 'Funeral/Burial'),
            ('counseling', 'Pastoral Counseling'),
            ('visitation', 'Home Visitation'),
            ('anointing', 'Anointing of Sick'),
            ('membership', 'Membership'),
            ('other', 'Other'),
        ]
    )
    
    # Request Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
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
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_requests'
    )
    
    # Request-specific data (JSON field)
    request_data = models.JSONField(default=dict, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'service_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member', 'status']),
            models.Index(fields=['type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.member.full_name} - {self.type} ({self.status})"
