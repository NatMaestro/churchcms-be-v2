"""
Service request serializers.
"""

from rest_framework import serializers
from .models import ServiceRequest


class ServiceRequestSerializer(serializers.ModelSerializer):
    """Service request serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'member', 'member_name', 'type', 'title', 'description',
            'status', 'priority', 'assigned_to', 'assigned_to_name',
            'request_data', 'notes', 'admin_notes', 'created_at', 'updated_at',
            'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """Simplified service request serializer for list views."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'member_name', 'type', 'title', 'status', 'priority',
            'created_at'
        ]

