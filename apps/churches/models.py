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
    
    # Subscription/Trial Management
    trial_started_at = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    grace_period_days = models.IntegerField(default=7, help_text="Days after expiration before blocking access")
    bypass_subscription_check = models.BooleanField(
        default=False,
        help_text="If True, this church bypasses all subscription/trial expiration checks. Use for testing or special cases."
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
    
    # Import subscription payment model
    # This allows accessing SubscriptionPayment via Church.subscription_payments
    
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
    
    def get_subscription_status(self):
        """
        Determine the current subscription status.
        Returns: 'active', 'trial_expired', 'subscription_expired', 'suspended', 'cancelled'
        """
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        # Check if cancelled or suspended
        if self.subscription_status in ['cancelled', 'suspended']:
            return self.subscription_status
        
        # Check if trial expired
        if self.plan == 'trial' and self.trial_end_date:
            grace_period_end = self.trial_end_date + timedelta(days=self.grace_period_days)
            if now > grace_period_end:
                return 'trial_expired'
            if now > self.trial_end_date:
                return 'trial_expiring'  # In grace period
        
        # Check if subscription expired
        if self.subscription_end_date:
            grace_period_end = self.subscription_end_date + timedelta(days=self.grace_period_days)
            if now > grace_period_end:
                return 'subscription_expired'
            if now > self.subscription_end_date:
                return 'subscription_expiring'  # In grace period
        
        return 'active'
    
    def can_access_system(self):
        """Check if church can access the system based on subscription status."""
        status = self.get_subscription_status()
        return status == 'active' or status in ['trial_expiring', 'subscription_expiring']
    
    def get_days_until_expiration(self):
        """Get number of days until trial or subscription expires."""
        from django.utils import timezone
        
        now = timezone.now()
        
        if self.plan == 'trial' and self.trial_end_date:
            days = (self.trial_end_date - now).days
            return max(0, days)
        
        if self.subscription_end_date:
            days = (self.subscription_end_date - now).days
            return max(0, days)
        
        return None


class Domain(DomainMixin):
    """
    Domain model for tenant routing.
    Maps domains/subdomains to churches.
    """
    
    class Meta:
        db_table = 'domains'
    
    def __str__(self):
        return self.domain
