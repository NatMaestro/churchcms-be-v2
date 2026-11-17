"""
Altar call views: church staff only.

Staff record who came forward at a service (a member, or a visitor by name
and phone) and track their follow-up. Members never see altar-call records,
not even their own: the notes are pastoral.
"""

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AltarCall
from .serializers import AltarCallSerializer, AltarCallListSerializer
from core.member_context import is_church_staff


class IsChurchStaff(permissions.BasePermission):
    message = 'Altar-call records are for church staff only.'

    def has_permission(self, request, view):
        return is_church_staff(request.user)


class AltarCallViewSet(viewsets.ModelViewSet):
    """Altar call management viewset."""
    
    queryset = AltarCall.objects.all()
    serializer_class = AltarCallSerializer
    permission_classes = [permissions.IsAuthenticated, IsChurchStaff]
    filterset_fields = ['reason', 'service_type', 'follow_up_status']
    search_fields = ['member__first_name', 'member__last_name', 'visitor_name', 'notes']
    ordering_fields = ['service_date', 'created_at']
    
    def get_serializer_class(self):
        """Use simplified serializer for list views."""
        if self.action == 'list':
            return AltarCallListSerializer
        return AltarCallSerializer
    
    def get_queryset(self):
        """Every altar call in this church, newest service first."""
        return AltarCall.objects.select_related('member').order_by('-service_date', '-created_at')
    
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
