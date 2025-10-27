"""
Member serializers.
"""

from rest_framework import serializers
from .models import Member, MemberWorkflow


class MemberSerializer(serializers.ModelSerializer):
    """Member serializer."""
    
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Member
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class MemberListSerializer(serializers.ModelSerializer):
    """Simplified member serializer for list views."""
    
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Member
        fields = [
            'id', 'member_id', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'gender', 'date_of_birth', 'status',
            'membership_date', 'engagement_score'
        ]


class MemberDetailSerializer(MemberSerializer):
    """Detailed member serializer with relationships."""
    
    workflows = serializers.SerializerMethodField()
    
    class Meta(MemberSerializer.Meta):
        fields = MemberSerializer.Meta.fields
    
    def get_workflows(self, obj):
        """Get member workflows."""
        workflows = obj.workflows.all()[:5]  # Latest 5
        return MemberWorkflowSerializer(workflows, many=True).data


class MemberWorkflowSerializer(serializers.ModelSerializer):
    """Member workflow serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    
    class Meta:
        model = MemberWorkflow
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

