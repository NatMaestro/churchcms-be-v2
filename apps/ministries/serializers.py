"""
Ministry serializers.
"""

from rest_framework import serializers
from .models import Ministry, MinistryMembership


class MinistryMembershipSerializer(serializers.ModelSerializer):
    """Ministry membership serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    
    class Meta:
        model = MinistryMembership
        fields = ['id', 'ministry', 'member', 'member_name', 'role', 'status', 'joined_at', 'notes']
        read_only_fields = ['id', 'joined_at']


class MinistrySerializer(serializers.ModelSerializer):
    """Ministry serializer."""
    
    leader_name = serializers.CharField(source='leader.full_name', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Ministry
        fields = [
            'id', 'name', 'description', 'leader', 'leader_name', 'category',
            'meeting_schedule', 'location', 'max_capacity', 'is_active',
            'member_count', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_member_count(self, obj):
        """Get count of active members."""
        return obj.members.filter(ministrymembership__status='active').count()


class MinistryDetailSerializer(MinistrySerializer):
    """Detailed ministry serializer with memberships."""
    
    memberships = MinistryMembershipSerializer(source='ministrymembership_set', many=True, read_only=True)
    
    class Meta(MinistrySerializer.Meta):
        fields = MinistrySerializer.Meta.fields + ['memberships']

