"""
Church models for multi-tenancy.
Each church is a separate tenant with isolated data.
"""

from django.db import models
try:
    from django_tenants.models import TenantMixin, DomainMixin
except ImportError:
    # Fallback if django-tenants not installed yet
    class TenantMixin:
        pass
    class DomainMixin:
        pass


class Church(TenantMixin):
    """
    Church model - represents a tenant in the multi-tenant system.
    Each church has its own schema and isolated data.
    """
    
    # Basic Information
    name = models.CharField(max_length=255)
    denomination = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    website = models.URLField(blank=True)
    subdomain = models.CharField(max_length=63, unique=True, db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    plan = models.CharField(
        max_length=20,
        choices=[
            ('trial', 'Trial'),
            ('basic', 'Basic'),
            ('standard', 'Standard'),
            ('premium', 'Premium'),
            ('enterprise', 'Enterprise'),
        ],
        default='trial'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('suspended', 'Suspended'),
            ('cancelled', 'Cancelled'),
        ],
        default='active'
    )
    
    # Branding Settings (JSON field)
    branding_settings = models.JSONField(default=dict, blank=True)
    
    # Feature Settings (JSON field)
    features = models.JSONField(default=dict, blank=True)
    
    # Payment Settings (JSON field)
    payment_settings = models.JSONField(default=dict, blank=True)
    
    # Member Settings (JSON field)
    member_settings = models.JSONField(default=dict, blank=True)
    
    # Communication Settings (JSON field)
    communication_settings = models.JSONField(default=dict, blank=True)
    
    # Privacy Settings (JSON field)
    privacy_settings = models.JSONField(default=dict, blank=True)
    
    # Automation Settings (JSON field)
    automation_settings = models.JSONField(default=dict, blank=True)
    
    # Integration Settings (JSON field)
    integration_settings = models.JSONField(default=dict, blank=True)
    
    # Service Request Types (JSON field)
    service_request_types = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Auto-drop schema on delete
    auto_drop_schema = False
    auto_create_schema = True
    
    class Meta:
        db_table = 'churches'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_default_features(self):
        """Get default features based on denomination."""
        defaults = {
            # Core features (enabled by default)
            'events': True,
            'announcements': True,
            'tithing': True,
            'offerings': True,
            'smallGroups': True,
            'volunteerManagement': True,
            'serviceRequests': True,
            'pastoralNotes': True,
            'membershipWorkflows': True,
            
            # Denomination-specific features
            'sacraments': self.denomination in ['Catholic', 'Anglican', 'Orthodox', 'Lutheran'],
            'liturgicalCalendar': self.denomination in ['Catholic', 'Anglican', 'Lutheran'],
            'altarCalls': self.denomination in ['Pentecostal', 'Non-denominational', 'Baptist'],
            'prayerRequests': True,  # All denominations
            'certificates': self.denomination in ['Catholic', 'Anglican'],
            'reconciliation': self.denomination in ['Catholic'],
            'anointingOfSick': self.denomination in ['Catholic'],
            'holyOrders': self.denomination in ['Catholic'],
            'pledges': self.denomination not in ['Catholic'],  # More common in Protestant churches
            'sabbathScheduling': self.denomination in ['Seventh-day Adventist'],
            'healthMinistries': self.denomination in ['Seventh-day Adventist'],
            'elderRoles': self.denomination in ['Presbyterian', 'Reformed'],
            'sessionNotes': self.denomination in ['Presbyterian', 'Reformed'],
            'documents': True,
        }
        
        # Merge with existing features
        if self.features:
            defaults.update(self.features)
        
        return defaults


class Domain(DomainMixin):
    """
    Domain model for tenant routing.
    Maps domains/subdomains to churches.
    """
    
    class Meta:
        db_table = 'domains'
    
    def __str__(self):
        return self.domain
