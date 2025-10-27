"""
Notification views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationPreferenceSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    """Notification management viewset."""
    
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['type', 'priority', 'is_read']
    ordering_fields = ['created_at', 'priority']
    
    def get_serializer_class(self):
        """Use simplified serializer for list views."""
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer
    
    def get_queryset(self):
        """Filter notifications for current user."""
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Get unread notifications.
        
        GET /api/v1/notifications/unread/
        """
        unread = self.get_queryset().filter(is_read=False)
        serializer = NotificationListSerializer(unread, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications.
        
        GET /api/v1/notifications/unread/count/
        """
        count = self.get_queryset().filter(is_read=False).count()
        
        return Response({
            'success': True,
            'count': count
        })
    
    @action(detail=True, methods=['put', 'patch'])
    def mark_read(self, request, pk=None):
        """
        Mark notification as read.
        
        PUT /api/v1/notifications/:id/mark-read/
        """
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return Response({
            'success': True,
            'message': 'Marked as read'
        })
    
    @action(detail=False, methods=['put'])
    def mark_all_read(self, request):
        """
        Mark all notifications as read.
        
        PUT /api/v1/notifications/mark-all-read/
        """
        self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'success': True,
            'message': 'All notifications marked as read'
        })
    
    @action(detail=True, methods=['delete'])
    def dismiss(self, request, pk=None):
        """
        Dismiss notification.
        
        DELETE /api/v1/notifications/:id/dismiss/
        """
        notification = self.get_object()
        notification.dismissed_at = timezone.now()
        notification.save()
        
        return Response({
            'success': True,
            'message': 'Notification dismissed'
        })


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """Notification preference management viewset."""
    
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter preferences for current user."""
        return NotificationPreference.objects.filter(user=self.request.user)
