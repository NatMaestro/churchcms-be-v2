"""
Prayer request serializers.
"""

from rest_framework import serializers
from .models import PrayerRequest


class PrayerRequestSerializer(serializers.ModelSerializer):
    """Prayer request serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    
    class Meta:
        model = PrayerRequest
        fields = [
            'id', 'member', 'member_name', 'requester_name', 'requester_email',
            'requester_phone', 'title', 'description', 'category', 'urgency',
            'is_confidential', 'is_public', 'status', 'assigned_to', 'assigned_to_name',
            'prayer_team_members', 'answered_at', 'answer_testimony', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PrayerRequestListSerializer(serializers.ModelSerializer):
    """Simplified prayer request serializer for list views."""
    
    requester = serializers.SerializerMethodField()
    
    class Meta:
        model = PrayerRequest
        fields = [
            'id', 'requester', 'title', 'category', 'urgency', 'status',
            'is_confidential', 'created_at'
        ]
    
    def get_requester(self, obj):
        """Get requester name (member or anonymous)."""
        if obj.member:
            return obj.member.full_name
        return obj.requester_name or 'Anonymous'

