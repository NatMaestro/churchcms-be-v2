"""
Authentication models.
Custom user model with church (tenant) relationship.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model.
    Users belong to churches (tenants) except for superadmins.
    """
    
    # Basic Information
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    
    # Church/Tenant relationship
    church = models.ForeignKey(
        'churches.Church',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )
    
    # Role
    role = models.CharField(
        max_length=20,
        choices=[
            ('superadmin', 'Super Admin'),
            ('admin', 'Admin'),
            ('member', 'Member'),
        ],
        default='member'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    
    # Password Management
    last_password_change = models.DateTimeField(null=True, blank=True)
    password_history = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    @property
    def is_superadmin(self):
        """Check if user is a superadmin."""
        return self.role == 'superadmin'
    
    @property
    def is_church_admin(self):
        """Check if user is a church admin."""
        return self.role == 'admin'
    
    @property
    def is_member(self):
        """Check if user is a member."""
        return self.role == 'member'


class PasswordResetToken(models.Model):
    """
    Password reset tokens.
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    email = models.EmailField()
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reset token for {self.email}"
    
    def is_valid(self):
        """Check if token is still valid."""
        return not self.used and timezone.now() < self.expires_at


class UserActivity(models.Model):
    """
    Track user activity for audit logging.
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=100)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_activities'
        ordering = ['-created_at']
        verbose_name_plural = 'User activities'
    
    def __str__(self):
        return f"{self.user.name} - {self.action} at {self.created_at}"
