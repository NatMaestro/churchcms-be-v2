"""
Member serializers.
"""

import time
from rest_framework import serializers
from .models import Member, MemberWorkflow, MemberRequest


class MemberSerializer(serializers.ModelSerializer):
    """Member serializer."""
    
    full_name = serializers.CharField(read_only=True)
    # Make member_id optional for creation (will be auto-generated if not provided)
    member_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Member
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate and auto-generate member_id if not provided."""
        member_id = attrs.get('member_id', '')
        if isinstance(member_id, str):
            member_id = member_id.strip()
        
        if not member_id:
            # Auto-generate member ID with church prefix
            from django.db import connection
            from apps.churches.models import Church
            import re
            
            # Get current tenant (church)
            try:
                tenant = connection.get_tenant()
                if tenant and isinstance(tenant, Church):
                    # Get prefix from church settings or generate from subdomain
                    member_settings = tenant.member_settings or {}
                    prefix = member_settings.get('memberIdPrefix') or \
                             tenant.subdomain.upper()[:2] or \
                             tenant.name[:2].upper()
                    
                    # Get existing members to find next number
                    existing_members = Member.objects.filter(
                        member_id__startswith=prefix
                    ).order_by('-member_id')
                    
                    # Extract highest number
                    start_number = member_settings.get('memberIdStartNumber', 1)
                    if existing_members.exists():
                        # Get the last member ID and extract number
                        last_id = existing_members.first().member_id
                        numbers = re.findall(r'\d+', last_id.replace(prefix, ''))
                        if numbers:
                            next_number = int(numbers[-1]) + 1
                        else:
                            next_number = start_number
                    else:
                        next_number = start_number
                    
                    # Format: PREFIX-0001
                    formatted_number = str(next_number).zfill(4)
                    attrs['member_id'] = f"{prefix}-{formatted_number}"
                else:
                    raise serializers.ValidationError({
                        'member_id': 'Could not determine church context for auto-generation'
                    })
            except Exception as e:
                # Fallback: use timestamp-based ID
                attrs['member_id'] = f"MEM-{str(int(time.time()))[-6:]}"
        
        return attrs


class MemberListSerializer(serializers.ModelSerializer):
    """Simplified member serializer for list views."""
    
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Member
        fields = [
            'id', 'member_id', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'gender', 'date_of_birth', 'status',
            'membership_date', 'created_at', 'engagement_score'
        ]
        read_only_fields = ['id', 'created_at']


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


class MemberRequestSerializer(serializers.ModelSerializer):
    """Member request serializer for admin views."""
    
    church_name = serializers.CharField(source='church.name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.name', read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.name', read_only=True)
    
    class Meta:
        model = MemberRequest
        fields = '__all__'
        read_only_fields = ['id', 'submitted_at', 'updated_at', 'created_member', 'created_user']


class MemberRequestListSerializer(serializers.ModelSerializer):
    """Simplified member request serializer for list views."""
    
    church_name = serializers.CharField(source='church.name', read_only=True)
    
    class Meta:
        model = MemberRequest
        fields = [
            'id', 'name', 'email', 'phone', 'status', 'church', 'church_name',
            'submitted_at', 'reviewed_at', 'confirmed_at'
        ]


class MemberRequestPublicSerializer(serializers.ModelSerializer):
    """Public serializer for submitting member requests (no auth required)."""
    
    class Meta:
        model = MemberRequest
        fields = [
            'name', 'email', 'phone', 'address', 'date_of_birth', 'gender',
            'marital_status', 'occupation', 'emergency_contact', 'church_experience',
            'reason_for_joining', 'how_did_you_hear', 'special_needs', 'skills', 'interests'
        ]
    
    def validate_email(self, value):
        """Check if email already has a pending/approved request for this church."""
        # This will be validated in the view where we have church context
        return value






