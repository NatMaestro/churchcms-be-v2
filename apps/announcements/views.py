"""
Announcement views.
"""

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Announcement
from .serializers import AnnouncementSerializer, AnnouncementListSerializer
from core.permissions import IsAdminOrReadOnly


class AnnouncementViewSet(viewsets.ModelViewSet):
    """Announcement management viewset."""
    
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['type', 'priority', 'target_audience', 'is_active']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'priority']
    
    def get_serializer_class(self):
        """Use simplified serializer for list views."""
        if self.action == 'list':
            return AnnouncementListSerializer
        return AnnouncementSerializer
    
    def get_queryset(self):
        """Filter announcements."""
        return Announcement.objects.filter(is_active=True).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent announcements (last 30 days).
        
        GET /api/v1/announcements/recent/
        """
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent = self.get_queryset().filter(
            created_at__gte=thirty_days_ago
        )
        
        serializer = AnnouncementListSerializer(recent, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def urgent(self, request):
        """
        Get urgent announcements.
        
        GET /api/v1/announcements/urgent/
        """
        urgent = self.get_queryset().filter(is_urgent=True)
        serializer = AnnouncementListSerializer(urgent, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
