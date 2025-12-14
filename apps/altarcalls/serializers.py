"""
Altar call serializers.
"""

from rest_framework import serializers
from .models import AltarCall


class AltarCallSerializer(serializers.ModelSerializer):
    """Altar call serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    
    class Meta:
        model = AltarCall
        fields = [
            'id', 'member', 'member_name', 'service_date', 'service_type', 'reason',
            'notes', 'follow_up_required', 'follow_up_status', 'follow_up_notes',
            'assigned_to', 'assigned_to_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AltarCallListSerializer(serializers.ModelSerializer):
    """Simplified altar call serializer for list views."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    
    class Meta:
        model = AltarCall
        fields = [
            'id', 'member_name', 'service_date', 'service_type', 'reason',
            'follow_up_status', 'created_at'
        ]






