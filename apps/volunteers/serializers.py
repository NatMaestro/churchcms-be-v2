"""
Volunteer serializers.
"""

from rest_framework import serializers
from .models import VolunteerOpportunity, VolunteerSignup, VolunteerHours


class VolunteerOpportunitySerializer(serializers.ModelSerializer):
    """Volunteer opportunity serializer."""
    
    ministry_name = serializers.CharField(source='ministry.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = VolunteerOpportunity
        fields = [
            'id', 'title', 'description', 'category', 'ministry', 'ministry_name',
            'location', 'start_date', 'end_date', 'schedule', 'recurrence_pattern',
            'spots_available', 'spots_filled', 'is_full', 'requirements', 'hours_per_week',
            'commitment', 'contact_person', 'contact_email', 'contact_phone',
            'is_active', 'is_urgent', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class VolunteerSignupSerializer(serializers.ModelSerializer):
    """Volunteer signup serializer."""
    
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    
    class Meta:
        model = VolunteerSignup
        fields = [
            'id', 'opportunity', 'opportunity_title', 'member', 'member_name', 'user',
            'status', 'approved_by', 'approved_at', 'notes', 'admin_notes',
            'hours_completed', 'completed_date', 'feedback', 'signup_date'
        ]
        read_only_fields = ['id', 'signup_date', 'approved_at']


class VolunteerHoursSerializer(serializers.ModelSerializer):
    """Volunteer hours serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    
    class Meta:
        model = VolunteerHours
        fields = [
            'id', 'member', 'member_name', 'opportunity', 'opportunity_title',
            'signup', 'hours', 'date', 'description', 'verified_by', 'verified_at',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'verified_at']






