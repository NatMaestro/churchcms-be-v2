"""
Church serializers.
"""

from rest_framework import serializers
from .models import Church, Domain


class DomainSerializer(serializers.ModelSerializer):
    """Domain serializer."""
    
    class Meta:
        model = Domain
        fields = ['id', 'domain', 'is_primary']


# Settings members of the church must not read (integration settings may hold service credentials).
STAFF_ONLY_SETTINGS = ('integration_settings',)


class ChurchSerializer(serializers.ModelSerializer):
    """Church serializer."""
    
    domains = DomainSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = getattr(self.context.get('request'), 'user', None)
        if not (user and user.is_authenticated and (user.is_church_admin or user.is_superadmin)):
            for name in STAFF_ONLY_SETTINGS:
                data.pop(name, None)
        return data
    
    class Meta:
        model = Church
        fields = [
            'id', 'schema_name', 'name', 'denomination', 'address', 
            'phone', 'email', 'website', 'subdomain', 'is_active', 
            'plan', 'subscription_status', 
            'trial_started_at', 'trial_end_date',
            'subscription_start_date', 'subscription_end_date',
            'grace_period_days', 'bypass_subscription_check',
            'branding_settings', 
            'features', 'payment_settings', 'member_settings',
            'communication_settings', 'privacy_settings',
            'automation_settings', 'integration_settings',
            'service_request_types', 'created_at', 'updated_at',
            'domains'
        ]
        # Subscription fields change only through payments or platform-admin
        # actions; a church must not be able to give itself time or free access.
        read_only_fields = [
            'id', 'schema_name', 'created_at', 'updated_at',
            'plan', 'subscription_status', 'trial_started_at', 'trial_end_date',
            'subscription_start_date', 'subscription_end_date', 'grace_period_days',
            'bypass_subscription_check',
        ]


class PublicChurchSerializer(serializers.ModelSerializer):
    """What anyone may see about a church, without logging in.

    Never add settings, subscription or schema fields here: this backs public,
    unauthenticated endpoints.
    """

    class Meta:
        model = Church
        fields = ['name', 'subdomain', 'denomination', 'address', 'phone', 'email', 'website']
        read_only_fields = fields


class ChurchDetailSerializer(ChurchSerializer):
    """Detailed church serializer with additional computed fields."""
    
    member_count = serializers.SerializerMethodField()
    event_count = serializers.SerializerMethodField()
    
    class Meta(ChurchSerializer.Meta):
        fields = ChurchSerializer.Meta.fields + ['member_count', 'event_count']
    
    def get_member_count(self, obj):
        """Get total member count."""
        # Note: This requires accessing tenant schema
        return 0  # Placeholder
    
    def get_event_count(self, obj):
        """Get total event count."""
        return 0  # Placeholder






