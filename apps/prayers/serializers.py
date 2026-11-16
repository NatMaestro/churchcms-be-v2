"""
Prayer request serializers.

Church staff use PrayerRequestSerializer, which includes the requester's
contact details. Members use PrayerRequestListSerializer to read (never any
contact details) and MemberPrayerRequestSerializer to submit or edit their
own requests.
"""

from rest_framework import serializers
from .models import PrayerRequest


def _viewer_member_id(serializer):
    """The signed-in person's member id, passed in by the viewset (None if they have no member record)."""
    return serializer.context.get('viewer_member_id')


class PrayerRequestSerializer(serializers.ModelSerializer):
    """Prayer request serializer (church staff)."""

    member_name = serializers.CharField(source='member.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    # How staff reach a member who asked through the portal (visitors give requester_* instead).
    member_email = serializers.CharField(source='member.email', read_only=True, default='')
    member_phone = serializers.CharField(source='member.phone', read_only=True, default='')
    prayer_count = serializers.SerializerMethodField()

    class Meta:
        model = PrayerRequest
        fields = [
            'id', 'member', 'member_name', 'requester_name', 'requester_email',
            'requester_phone', 'member_email', 'member_phone', 'title', 'description', 'category', 'urgency',
            'is_confidential', 'is_public', 'status', 'assigned_to', 'assigned_to_name',
            'prayer_team_members', 'prayer_count', 'answered_at', 'answer_testimony',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_prayer_count(self, obj):
        return len(obj.prayer_team_members or [])


class PrayerRequestListSerializer(serializers.ModelSerializer):
    """Prayer request as a member (or a list) sees it: no contact details."""

    requester = serializers.SerializerMethodField()
    prayer_count = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    i_prayed = serializers.SerializerMethodField()

    class Meta:
        model = PrayerRequest
        fields = [
            'id', 'requester', 'title', 'description', 'category', 'urgency', 'status',
            'is_confidential', 'is_public', 'prayer_count', 'is_mine', 'i_prayed',
            'answered_at', 'answer_testimony', 'created_at'
        ]

    def get_requester(self, obj):
        """Get requester name (member or anonymous)."""
        if obj.member:
            return obj.member.full_name
        return obj.requester_name or 'Anonymous'

    def get_prayer_count(self, obj):
        return len(obj.prayer_team_members or [])

    def get_is_mine(self, obj):
        viewer = _viewer_member_id(self)
        return viewer is not None and obj.member_id == viewer

    def get_i_prayed(self, obj):
        viewer = _viewer_member_id(self)
        return viewer is not None and viewer in (obj.prayer_team_members or [])


class MemberPrayerRequestSerializer(serializers.ModelSerializer):
    """What a member may set on their own prayer request."""

    class Meta:
        model = PrayerRequest
        fields = ['id', 'title', 'description', 'category', 'urgency', 'is_public', 'is_confidential']
        read_only_fields = ['id']

    def validate(self, attrs):
        # A confidential request is for the church's pastors only, so it is never shared with members.
        is_confidential = attrs.get('is_confidential', getattr(self.instance, 'is_confidential', False))
        if is_confidential:
            attrs['is_public'] = False
        return attrs
