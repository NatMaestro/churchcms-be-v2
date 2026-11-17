"""
Altar call serializers (church staff only; see views).
"""

from rest_framework import serializers
from .models import AltarCall


class AltarCallSerializer(serializers.ModelSerializer):
    """Altar call serializer."""

    member_name = serializers.CharField(source='member.full_name', read_only=True)
    person_name = serializers.CharField(read_only=True)
    # How staff reach a member who came forward (visitors give visitor_phone).
    member_phone = serializers.CharField(source='member.phone', read_only=True, default='')
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)

    class Meta:
        model = AltarCall
        fields = [
            'id', 'member', 'member_name', 'member_phone', 'visitor_name', 'visitor_phone', 'person_name',
            'service_date', 'service_type', 'reason',
            'notes', 'follow_up_required', 'follow_up_status', 'follow_up_notes',
            'assigned_to', 'assigned_to_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        member = attrs.get('member', getattr(self.instance, 'member', None))
        visitor_name = (attrs.get('visitor_name', getattr(self.instance, 'visitor_name', '')) or '').strip()
        if member is None and not visitor_name:
            raise serializers.ValidationError({'visitor_name': 'Choose a member or enter the visitor\'s name.'})
        if member is not None:
            # A record is for a member or a visitor, never both.
            attrs['visitor_name'] = ''
            attrs['visitor_phone'] = ''
        elif 'visitor_name' in attrs:
            attrs['visitor_name'] = visitor_name
        return attrs


class AltarCallListSerializer(serializers.ModelSerializer):
    """Simplified altar call serializer for list views."""

    member_name = serializers.CharField(source='member.full_name', read_only=True)
    person_name = serializers.CharField(read_only=True)

    class Meta:
        model = AltarCall
        fields = [
            'id', 'member', 'member_name', 'visitor_name', 'person_name', 'service_date', 'service_type',
            'reason', 'follow_up_required', 'follow_up_status', 'created_at'
        ]
