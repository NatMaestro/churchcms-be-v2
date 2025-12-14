"""
Notification serializers.
"""

from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer."""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'type', 'title', 'message', 'priority', 'category',
            'action_type', 'action_url', 'metadata', 'data', 'is_read', 'read_at',
            'dismissed_at', 'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at', 'dismissed_at']


class NotificationListSerializer(serializers.ModelSerializer):
    """Simplified notification serializer for list views."""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'title', 'message', 'priority', 'is_read', 'created_at'
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Notification preference serializer."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'channel', 'category', 'enabled', 'frequency',
            'quiet_hours_start', 'quiet_hours_end', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']






