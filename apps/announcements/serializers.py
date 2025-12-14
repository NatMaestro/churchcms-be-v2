"""
Announcement serializers.
"""

from rest_framework import serializers
from .models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    """Announcement serializer."""
    
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'type', 'priority', 'target_audience',
            'is_active', 'is_urgent', 'scheduled_at', 'expires_at', 'is_expired',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class AnnouncementListSerializer(serializers.ModelSerializer):
    """Simplified announcement serializer for list views."""
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'type', 'priority', 'target_audience',
            'is_active', 'is_urgent', 'created_at'
        ]






