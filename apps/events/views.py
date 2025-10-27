"""
Event views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Event, EventRegistration
from .serializers import (
    EventSerializer,
    EventListSerializer,
    EventDetailSerializer,
    EventRegistrationSerializer
)
from core.permissions import IsAdminOrReadOnly
from core.services import ExportService


class EventViewSet(viewsets.ModelViewSet):
    """Event management viewset."""
    
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['type', 'is_recurring']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['date', 'created_at', 'title']
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action."""
        if self.action == 'list':
            return EventListSerializer
        elif self.action == 'retrieve':
            return EventDetailSerializer
        return EventSerializer
    
    def get_queryset(self):
        """Filter events by current tenant."""
        return Event.objects.all().order_by('date')
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Get upcoming events.
        
        GET /api/v1/events/upcoming/
        """
        upcoming_events = Event.objects.filter(
            date__gte=timezone.now()
        ).order_by('date')
        
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
        
        # Check if event is full
        if event.is_full:
            return Response({
                'success': False,
                'error': 'Event is at capacity'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        member_id = request.data.get('member_id')
        registration_data = request.data.get('registration_data', {})
        
        if not member_id:
            return Response({
                'success': False,
                'error': 'member_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or get registration
        registration, created = EventRegistration.objects.get_or_create(
            event=event,
            member_id=member_id,
            defaults={'registration_data': registration_data}
        )
        
        if not created:
            return Response({
                'success': False,
                'error': 'Already registered for this event'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Add to attendees list
        if not event.attendees:
            event.attendees = []
        if member_id not in event.attendees:
            event.attendees.append(member_id)
            event.save()
        
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
        member_id = request.data.get('member_id')
        
        try:
            registration = EventRegistration.objects.get(event=event, member_id=member_id)
            registration.delete()
            
            # Remove from attendees list
            if event.attendees and member_id in event.attendees:
                event.attendees.remove(member_id)
                event.save()
            
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
