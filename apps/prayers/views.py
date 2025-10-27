"""
Prayer request views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import models
from .models import PrayerRequest
from .serializers import PrayerRequestSerializer, PrayerRequestListSerializer


class PrayerRequestViewSet(viewsets.ModelViewSet):
    """Prayer request management viewset."""
    
    queryset = PrayerRequest.objects.all()
    serializer_class = PrayerRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['category', 'urgency', 'status', 'is_public']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'urgency', 'status']
    
    def get_serializer_class(self):
        """Use simplified serializer for list views."""
        if self.action == 'list':
            return PrayerRequestListSerializer
        return PrayerRequestSerializer
    
    def get_queryset(self):
        """Filter prayer requests."""
        user = self.request.user
        queryset = PrayerRequest.objects.all()
        
        # Admins see all
        if user.is_church_admin or user.is_superadmin:
            return queryset
        
        # Members see:
        # 1. Their own requests
        # 2. Public requests
        # 3. Non-confidential requests
        if hasattr(user, 'member_profile'):
            return queryset.filter(
                models.Q(member=user.member_profile) |
                models.Q(is_public=True, is_confidential=False)
            )
        
        return queryset.filter(is_public=True, is_confidential=False)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get active prayer requests.
        
        GET /api/v1/prayer-requests/active/
        """
        active_requests = self.get_queryset().filter(status='active')
        serializer = PrayerRequestListSerializer(active_requests, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'])
    def mark_answered(self, request, pk=None):
        """
        Mark prayer request as answered.
        
        PATCH /api/v1/prayer-requests/:id/mark-answered/
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
