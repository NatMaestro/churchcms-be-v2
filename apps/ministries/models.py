"""
Ministry models.
Small groups and ministry management.
"""

from django.db import models
from django.conf import settings


class Ministry(models.Model):
    """
    Ministry/Small Group model.
    """
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Leader
    leader = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        related_name='led_ministries'
    )
    
    # Category
    category = models.CharField(
        max_length=50,
        choices=[
            ('worship', 'Worship'),
            ('youth', 'Youth'),
            ('children', 'Children'),
            ('prayer', 'Prayer'),
            ('outreach', 'Outreach'),
            ('pastoral', 'Pastoral'),
            ('education', 'Education'),
            ('other', 'Other'),
        ]
    )
    
    # Members
    members = models.ManyToManyField(
        'members.Member',
        through='MinistryMembership',
        related_name='ministries'
    )
    
    # Schedule
    meeting_schedule = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    
    # Capacity
    max_capacity = models.IntegerField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_ministries'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ministries'
        ordering = ['name']
        verbose_name_plural = 'Ministries'
    
    def __str__(self):
        return self.name


class MinistryMembership(models.Model):
    """
    Ministry membership linking members to ministries.
    """
    
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE)
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE)
    
    role = models.CharField(
        max_length=20,
        choices=[
            ('member', 'Member'),
            ('leader', 'Leader'),
            ('assistant', 'Assistant'),
        ],
        default='member'
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        ],
        default='active'
    )
    
    joined_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'ministry_memberships'
        unique_together = ['ministry', 'member']
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.member.full_name} - {self.ministry.name} ({self.role})"
