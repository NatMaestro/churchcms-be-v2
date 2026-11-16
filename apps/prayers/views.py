"""
Prayer request views.

Church staff see every request (with the requester's contact details) and
manage them: status, answer, assignment. A member sees their own requests
plus requests other members chose to share (public and not confidential),
submits requests as themselves, edits or withdraws only their own, and can
record that they prayed for one. See core.member_context.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import models, transaction

from core.member_context import is_church_staff, member_for
from .models import PrayerRequest
from .serializers import (
    MemberPrayerRequestSerializer,
    PrayerRequestListSerializer,
    PrayerRequestSerializer,
)

MEMBER_WRITE_ACTIONS = ('update', 'partial_update', 'destroy', 'mark_answered')


class PrayerRequestViewSet(viewsets.ModelViewSet):
    """Prayer request management viewset."""

    queryset = PrayerRequest.objects.all()
    serializer_class = PrayerRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['category', 'urgency', 'status', 'is_public']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'urgency', 'status']

    def _viewer(self):
        """The signed-in person's member record in this church (cached per request)."""
        if not hasattr(self, '_viewer_member'):
            self._viewer_member = member_for(self.request.user)
        return self._viewer_member

    def get_serializer_context(self):
        context = super().get_serializer_context()
        viewer = self._viewer()
        context['viewer_member_id'] = viewer.pk if viewer else None
        return context

    def get_serializer_class(self):
        """Staff get the full record; members never see contact details."""
        if is_church_staff(self.request.user):
            return PrayerRequestListSerializer if self.action == 'list' else PrayerRequestSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return MemberPrayerRequestSerializer
        return PrayerRequestListSerializer

    def get_queryset(self):
        """Staff: everything. Members: their own, plus shared ones (and only their own to change)."""
        queryset = PrayerRequest.objects.select_related('member')
        if is_church_staff(self.request.user):
            return queryset

        viewer = self._viewer()
        if self.action in MEMBER_WRITE_ACTIONS:
            return queryset.filter(member=viewer) if viewer else queryset.none()

        shared = models.Q(is_public=True, is_confidential=False)
        return queryset.filter(shared | models.Q(member=viewer)) if viewer else queryset.filter(shared)

    def create(self, request, *args, **kwargs):
        if not is_church_staff(request.user) and self._viewer() is None:
            return Response({
                'success': False,
                'error': 'No member record is linked to this account.'
            }, status=status.HTTP_400_BAD_REQUEST)
        response = super().create(request, *args, **kwargs)
        if not is_church_staff(request.user):
            # Answer with the member view of the saved request.
            response.data = PrayerRequestListSerializer(self._saved, context=self.get_serializer_context()).data
        return response

    def perform_create(self, serializer):
        """A member's request is always their own; staff may record one for anyone."""
        if is_church_staff(self.request.user):
            self._saved = serializer.save()
        else:
            self._saved = serializer.save(member=self._viewer(), status='active')

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if not is_church_staff(request.user):
            # Answer with the member view of the saved request.
            response.data = PrayerRequestListSerializer(
                self.get_object(), context=self.get_serializer_context()
            ).data
        return response

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get active prayer requests.

        GET /api/v1/prayer-requests/active/
        """
        active_requests = self.get_queryset().filter(status='active')
        serializer = PrayerRequestListSerializer(active_requests, many=True, context=self.get_serializer_context())

        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def pray(self, request, pk=None):
        """
        Record that the signed-in member prayed for this request. Doing it again changes nothing.

        POST /api/v1/prayer-requests/:id/pray/  ->  {"success": true, "prayer_count": n, "i_prayed": true}
        """
        prayer_request = self.get_object()  # only requests this person can see
        viewer = self._viewer()
        if viewer is None:
            return Response({
                'success': False,
                'error': 'No member record is linked to this account.'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Lock the row so two people praying at once are both counted.
            prayer_request = PrayerRequest.objects.select_for_update().get(pk=prayer_request.pk)
            praying = prayer_request.prayer_team_members or []
            if viewer.pk not in praying:
                prayer_request.prayer_team_members = praying + [viewer.pk]
                prayer_request.save(update_fields=['prayer_team_members', 'updated_at'])

        return Response({
            'success': True,
            'prayer_count': len(prayer_request.prayer_team_members),
            'i_prayed': True,
        })

    @action(detail=True, methods=['patch'])
    def mark_answered(self, request, pk=None):
        """
        Mark prayer request as answered (staff, or the member who asked).

        PATCH /api/v1/prayer-requests/:id/mark_answered/
        Body: { "testimony": "..." }
        """
        prayer_request = self.get_object()

        prayer_request.status = 'answered'
        prayer_request.answered_at = timezone.now()
        prayer_request.answer_testimony = request.data.get('testimony', '')
        prayer_request.save()

        return Response({
            'success': True,
            'message': 'Marked as answered'
        })
