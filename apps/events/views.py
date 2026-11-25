"""
Event views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone
from .models import Event, EventRegistration
from .serializers import (
    EventSerializer,
    EventListSerializer,
    EventDetailSerializer,
    EventRegistrationSerializer
)
from core.member_context import acting_member, is_church_staff
from core.permissions import IsAdminOrReadOnly
from core.services import ExportService

from apps.churches.module_access import requires_module

# Every endpoint here refuses while the church has this module switched off.
MODULE = requires_module('events')


class EventViewSet(viewsets.ModelViewSet):
    """Event management viewset."""
    
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly, MODULE]
    filterset_fields = ['type', 'is_recurring']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['date', 'created_at', 'title']
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action."""
        if self.action == 'list':
            return EventListSerializer
        elif self.action == 'retrieve':
            # Only church staff see who else registered.
            return EventDetailSerializer if is_church_staff(self.request.user) else EventSerializer
        return EventSerializer

    def get_permissions(self):
        """Any signed-in church user may register or unregister themselves."""
        if self.action in ('register', 'unregister'):
            return [permissions.IsAuthenticated(), MODULE()]
        return super().get_permissions()

    def _with_my_registration(self, events):
        """Mark each event with whether the signed-in person is registered for it."""
        mine = EventRegistration.objects.filter(event=OuterRef('pk'), member__user=self.request.user)
        return events.annotate(is_registered=Exists(mine))

    def get_queryset(self):
        """Filter events by current tenant."""
        return self._with_my_registration(Event.objects.all()).order_by('date')
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming events.
        
        GET /api/v1/events/upcoming/
        """
        upcoming_events = self._with_my_registration(Event.objects.filter(
            date__gte=timezone.now()
        )).order_by('date')
        
        serializer = EventListSerializer(upcoming_events, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def past(self, request):
        """
        Get past events.
        
        GET /api/v1/events/past/
        """
        past_events = Event.objects.filter(
            date__lt=timezone.now()
        ).order_by('-date')
        
        serializer = EventListSerializer(past_events, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        """
        Register for an event.
        
        POST /api/v1/events/:id/register/
        Body: { "member_id": "xxx", "registration_data": {...} }
        """
        event = self.get_object()
        member = acting_member(request)
        registration_data = request.data.get('registration_data', {})

        if member is None:
            return Response({
                'success': False,
                'error': 'No member record found to register.'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Lock the event so two registrations cannot both take the last place.
            event = Event.objects.select_for_update().get(pk=event.pk)
            if EventRegistration.objects.filter(event=event, member=member).exists():
                return Response({
                    'success': False,
                    'error': 'Already registered for this event'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if event is full
            if event.is_full:
                return Response({
                    'success': False,
                    'error': 'Event is at capacity'
                }, status=status.HTTP_400_BAD_REQUEST)

            registration = EventRegistration.objects.create(
                event=event, member=member, registration_data=registration_data,
            )

            # Add to attendees list
            attendees = event.attendees or []
            if member.pk not in attendees and str(member.pk) not in attendees:
                event.attendees = attendees + [member.pk]
                event.save(update_fields=['attendees'])
                
        return Response({
            'success': True,
            'message': 'Registered successfully',
            'registration': EventRegistrationSerializer(registration).data
        })
    
    @action(detail=True, methods=['delete'])
    def unregister(self, request, pk=None):
        """
        Unregister from an event.
        
        DELETE /api/v1/events/:id/unregister/
        Body: { "member_id": "xxx" }
        """
        event = self.get_object()
        member = acting_member(request)

        try:
            with transaction.atomic():
                event = Event.objects.select_for_update().get(pk=event.pk)
                registration = EventRegistration.objects.get(event=event, member=member)
                registration.delete()

                # Remove from attendees list (older rows may hold the id as text)
                attendees = event.attendees or []
                remaining = [a for a in attendees if a not in (member.pk, str(member.pk))]
                if remaining != attendees:
                    event.attendees = remaining
                    event.save(update_fields=['attendees'])
                        
            return Response({
                'success': True,
                'message': 'Unregistered successfully'
            })
        except EventRegistration.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Not registered for this event'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def attendees(self, request, pk=None):
        """
        Get event attendees.
        
        GET /api/v1/events/:id/attendees/
        """
        if not is_church_staff(request.user):
            return Response({
                'success': False,
                'error': 'Only church staff can see who registered.'
            }, status=status.HTTP_403_FORBIDDEN)
        event = self.get_object()
        registrations = EventRegistration.objects.filter(event=event)
        
        serializer = EventRegistrationSerializer(registrations, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """
        Export events to CSV.
        
        GET /api/v1/events/export-csv/
        """
        if not (request.user.is_church_admin or request.user.is_superadmin):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        queryset = self.filter_queryset(self.get_queryset())
        church_name = request.user.church.name if request.user.church else None
        
        return ExportService.export_events_csv(queryset, church_name)
