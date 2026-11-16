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
    spots_left = serializers.SerializerMethodField()
    # The signed-in person's sign-up status (pending, approved, ...), or null (set by the viewset).
    my_signup_status = serializers.SerializerMethodField()
    
    class Meta:
        model = VolunteerOpportunity
        fields = [
            'id', 'title', 'description', 'category', 'ministry', 'ministry_name',
            'location', 'start_date', 'end_date', 'schedule', 'recurrence_pattern',
            'spots_available', 'spots_filled', 'spots_left', 'is_full', 'my_signup_status',
            'requirements', 'hours_per_week',
            'commitment', 'contact_person', 'contact_email', 'contact_phone',
            'is_active', 'is_urgent', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'spots_filled']

    def get_spots_left(self, obj):
        """Open spots, or null when there is no limit."""
        if not obj.spots_available:
            return None
        return max(obj.spots_available - obj.spots_filled, 0)

    def get_my_signup_status(self, obj):
        return getattr(obj, 'my_signup_status', None)


class VolunteerSignupSerializer(serializers.ModelSerializer):
    """Volunteer signup serializer."""
    
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    # How staff reach the volunteer (a member only ever sees their own sign-ups).
    member_phone = serializers.CharField(source='member.phone', read_only=True, default='')
    member_email = serializers.CharField(source='member.email', read_only=True, default='')
    
    class Meta:
        model = VolunteerSignup
        fields = [
            'id', 'opportunity', 'opportunity_title', 'member', 'member_name', 'member_phone',
            'member_email', 'user', 'status', 'approved_by', 'approved_at', 'notes', 'admin_notes',
            'hours_completed', 'completed_date', 'feedback', 'signup_date'
        ]
        # Sign-ups are made through the opportunity's signup action; staff change the status.
        read_only_fields = ['id', 'signup_date', 'approved_at', 'approved_by', 'opportunity', 'member', 'user']


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






