"""
Altar call views.
"""

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AltarCall
from .serializers import AltarCallSerializer, AltarCallListSerializer
from core.permissions import IsAdminOrReadOnly


class AltarCallViewSet(viewsets.ModelViewSet):
    """Altar call management viewset."""
    
    queryset = AltarCall.objects.all()
    serializer_class = AltarCallSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['reason', 'service_type', 'follow_up_status']
    search_fields = ['member__first_name', 'member__last_name', 'notes']
    ordering_fields = ['service_date', 'created_at']
    
    def get_serializer_class(self):
        """Use simplified serializer for list views."""
        if self.action == 'list':
            return AltarCallListSerializer
        return AltarCallSerializer
    
    def get_queryset(self):
        """Filter altar calls."""
        return AltarCall.objects.all().order_by('-service_date')
    
    @action(detail=False, methods=['get'])
    def follow_up_pending(self, request):
        """
        Get altar calls needing follow-up.
        
        GET /api/v1/altar-calls/follow-up-pending/
        """
        pending = self.get_queryset().filter(
            follow_up_required=True,
            follow_up_status='pending'
        )
        
        serializer = AltarCallListSerializer(pending, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
