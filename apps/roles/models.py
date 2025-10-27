"""
Role and permission models.
"""

from django.db import models
from django.conf import settings


class Permission(models.Model):
    """
    System permissions.
    """
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Resource this permission applies to
    resource = models.CharField(
        max_length=50,
        choices=[
            ('members', 'Members'),
            ('events', 'Events'),
            ('payments', 'Payments'),
            ('announcements', 'Announcements'),
            ('roles', 'Roles'),
            ('settings', 'Settings'),
            ('analytics', 'Analytics'),
            ('reports', 'Reports'),
            ('documents', 'Documents'),
        ]
    )
    
    # Action
    action = models.CharField(
        max_length=20,
        choices=[
            ('read', 'Read'),
            ('write', 'Write'),
            ('create', 'Create'),
            ('delete', 'Delete'),
            ('manage', 'Manage'),
        ]
    )
    
    description = models.TextField(blank=True)
    is_system_permission = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'permissions'
        ordering = ['resource', 'action']
        unique_together = ['resource', 'action']
    
    def __str__(self):
        return f"{self.resource}.{self.action}"


class Role(models.Model):
    """
    User roles with permissions.
    """
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Permissions (JSON field matching frontend structure)
    permissions = models.JSONField(default=list)
    
    # Color and Icon for UI
    color = models.CharField(max_length=50, default='blue')
    icon = models.CharField(max_length=50, default='Shield')
    
    # Flags
    is_default = models.BooleanField(default=False)
    is_system_role = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'roles'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
    User role assignments.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_assignments'
    )
    
    # Assignment tracking
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_roles'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'user_roles'
        unique_together = ['user', 'role']
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.user.name} - {self.role.name}"
