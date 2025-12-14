"""
Event serializers.
"""

from rest_framework import serializers
from .models import Event, EventRegistration


class EventRegistrationSerializer(serializers.ModelSerializer):
    """Event registration serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    
    class Meta:
        model = EventRegistration
        fields = ['id', 'event', 'member', 'member_name', 'registration_data', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


class EventSerializer(serializers.ModelSerializer):
    """Event serializer."""
    
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    attendee_count = serializers.SerializerMethodField()
    is_full = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'date', 'end_date', 'location', 'type',
            'capacity', 'requires_registration', 'registration_deadline', 'max_attendees',
            'registration_form', 'is_recurring', 'recurrence_pattern', 'recurrence_end_date',
            'attendees', 'attendee_count', 'is_full', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_attendee_count(self, obj):
        """Get count of attendees."""
        return len(obj.attendees) if obj.attendees else 0


class EventListSerializer(serializers.ModelSerializer):
    """Simplified event serializer for list views."""
    
    attendee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'date', 'end_date', 'location', 'type',
            'capacity', 'attendee_count', 'is_recurring', 'recurrence_pattern'
        ]
    
    def get_attendee_count(self, obj):
        return len(obj.attendees) if obj.attendees else 0


class EventDetailSerializer(EventSerializer):
    """Detailed event serializer with registrations."""
    
    registrations = EventRegistrationSerializer(many=True, read_only=True)
    
    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ['registrations']






