"""
Service request serializers.

Church staff use ServiceRequestSerializer (everything, including the member's
contact details). Members read their own requests through
ServiceRequestListSerializer and submit through MemberServiceRequestSerializer,
which only accepts what a member may set.
"""

from rest_framework import serializers
from .models import ServiceRequest


class ServiceRequestSerializer(serializers.ModelSerializer):
    """Service request serializer (church staff)."""

    member_name = serializers.CharField(source='member.full_name', read_only=True)
    # How staff reach the member who asked.
    member_email = serializers.CharField(source='member.email', read_only=True, default='')
    member_phone = serializers.CharField(source='member.phone', read_only=True, default='')
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'member', 'member_name', 'member_email', 'member_phone', 'type', 'title', 'description',
            'status', 'priority', 'assigned_to', 'assigned_to_name',
            'request_data', 'notes', 'admin_notes', 'created_at', 'updated_at',
            'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """
    A request as a list (and a member) sees it: no contact details.
    admin_notes is the church's reply to the member.
    """

    member_name = serializers.CharField(source='member.full_name', read_only=True)

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'member', 'member_name', 'type', 'title', 'description', 'status', 'priority',
            'request_data', 'notes', 'admin_notes', 'created_at', 'completed_at'
        ]


class MemberServiceRequestSerializer(serializers.ModelSerializer):
    """What a member may set when asking the church for a service."""

    PREFERRED_DATE_KEY = 'preferred_date'

    class Meta:
        model = ServiceRequest
        fields = ['id', 'type', 'title', 'description', 'priority', 'notes', 'request_data']
        read_only_fields = ['id']

    def validate_request_data(self, value):
        # Only a preferred date (YYYY-MM-DD) is accepted from members.
        value = value or {}
        preferred = value.get(self.PREFERRED_DATE_KEY)
        if not preferred:
            return {}
        try:
            serializers.DateField().to_internal_value(preferred)
        except serializers.ValidationError:
            raise serializers.ValidationError('preferred_date must be a date like 2026-12-07.')
        return {self.PREFERRED_DATE_KEY: preferred}
