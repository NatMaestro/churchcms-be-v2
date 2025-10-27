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


class ChurchSerializer(serializers.ModelSerializer):
    """Church serializer."""
    
    domains = DomainSerializer(many=True, read_only=True)
    
    class Meta:
        model = Church
        fields = [
            'id', 'schema_name', 'name', 'denomination', 'address', 
            'phone', 'email', 'website', 'subdomain', 'is_active', 
            'plan', 'subscription_status', 'branding_settings', 
            'features', 'payment_settings', 'member_settings',
            'communication_settings', 'privacy_settings',
            'automation_settings', 'integration_settings',
            'service_request_types', 'created_at', 'updated_at',
            'domains'
        ]
        read_only_fields = ['id', 'schema_name', 'created_at', 'updated_at']


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

