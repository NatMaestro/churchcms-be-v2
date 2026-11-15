"""
Public content for a church's own website (events, announcements, ministries).

Unauthenticated and read-only: a church website fetches it from the visitor's
browser. Requests arrive without a tenant header, so the view switches to the
named church's schema itself. Events and announcements appear only when the
admin ticked "show on website"; nothing that identifies a member (attendees,
authors, ministry leaders or members) is ever returned.
"""
from django.db.models import Q
from django.utils import timezone
from django_tenants.utils import tenant_context
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.announcements.models import Announcement
from apps.events.models import Event
from apps.ministries.models import Ministry

from .models import Church

WEBSITE_CONTENT_VERSION = 1
MAX_EVENTS = 50
MAX_ANNOUNCEMENTS = 10
MAX_MINISTRIES = 50


class WebsiteContentThrottle(AnonRateThrottle):
    """Per-IP limit on the public website feed (rate set in settings)."""

    scope = 'church_website_content'


class WebsiteEventSerializer(serializers.ModelSerializer):
    start = serializers.DateTimeField(source='date')
    end = serializers.DateTimeField(source='end_date')

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'start', 'end', 'location', 'type',
                  'is_recurring', 'recurrence_pattern']


class WebsiteAnnouncementSerializer(serializers.ModelSerializer):
    starts_at = serializers.DateTimeField(source='scheduled_at')

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'content', 'type', 'is_urgent', 'starts_at', 'expires_at']


class WebsiteMinistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ministry
        fields = ['id', 'name', 'description', 'category', 'meeting_schedule', 'location']


def _website_events(now):
    # Upcoming one-off events, plus recurring events whose series hasn't ended
    # (their stored date is the first occurrence, which may be in the past).
    still_recurring = Q(is_recurring=True) & (
        Q(recurrence_end_date__isnull=True) | Q(recurrence_end_date__gte=now.date())
    )
    return (Event.objects
            .filter(show_on_website=True)
            .filter(Q(date__gte=now) | still_recurring)
            .order_by('date')[:MAX_EVENTS])


def _website_announcements(now):
    return (Announcement.objects
            .filter(show_on_website=True, is_active=True)
            .filter(Q(scheduled_at__isnull=True) | Q(scheduled_at__lte=now))
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .order_by('-is_urgent', '-created_at')[:MAX_ANNOUNCEMENTS])


def _website_ministries():
    return Ministry.objects.filter(is_active=True).order_by('name')[:MAX_MINISTRIES]


@api_view(['GET'])
@permission_classes([permissions.AllowAny])  # Public: read by the church's own website.
@throttle_classes([WebsiteContentThrottle])
def church_website_content(request, subdomain):
    """
    GET /api/v1/churches/<subdomain>/website/

    Returns {version, events, announcements, ministries}. Unknown or inactive
    churches get 404.
    """
    try:
        church = Church.objects.get(subdomain=subdomain, is_active=True)
    except Church.DoesNotExist:
        return Response({'success': False, 'error': 'Church not found or inactive'},
                        status=status.HTTP_404_NOT_FOUND)

    now = timezone.now()
    with tenant_context(church):
        data = {
            'version': WEBSITE_CONTENT_VERSION,
            'events': WebsiteEventSerializer(_website_events(now), many=True).data,
            'announcements': WebsiteAnnouncementSerializer(_website_announcements(now), many=True).data,
            'ministries': WebsiteMinistrySerializer(_website_ministries(), many=True).data,
        }
    return Response(data)
