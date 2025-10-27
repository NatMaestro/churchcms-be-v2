"""
Ministry views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ministry, MinistryMembership
from .serializers import (
    MinistrySerializer,
    MinistryDetailSerializer,
    MinistryMembershipSerializer
)
from core.permissions import IsAdminOrReadOnly


class MinistryViewSet(viewsets.ModelViewSet):
    """Ministry management viewset."""
    
    queryset = Ministry.objects.all()
    serializer_class = MinistrySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve."""
        if self.action == 'retrieve':
            return MinistryDetailSerializer
        return MinistrySerializer
    
    def get_queryset(self):
        """Filter ministries by current tenant."""
        return Ministry.objects.filter(is_active=True).order_by('name')
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """
        Join a ministry.
        
        POST /api/v1/ministries/:id/join/
        Body: { "member_id": "xxx" }
        """
        ministry = self.get_object()
        member_id = request.data.get('member_id')
        
        if not member_id:
            return Response({
                'success': False,
                'error': 'member_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check capacity
        if ministry.max_capacity:
            current_members = ministry.members.filter(ministrymembership__status='active').count()
            if current_members >= ministry.max_capacity:
                return Response({
                    'success': False,
                    'error': 'Ministry is at capacity'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create membership
        membership, created = MinistryMembership.objects.get_or_create(
            ministry=ministry,
            member_id=member_id,
            defaults={'status': 'active', 'role': 'member'}
        )
        
        if not created:
            return Response({
                'success': False,
                'error': 'Already a member of this ministry'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': 'Joined ministry successfully',
            'membership': MinistryMembershipSerializer(membership).data
        })
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """
        Leave a ministry.
        
        POST /api/v1/ministries/:id/leave/
        Body: { "member_id": "xxx" }
        """
        ministry = self.get_object()
        member_id = request.data.get('member_id')
        
        try:
            membership = MinistryMembership.objects.get(
                ministry=ministry,
                member_id=member_id,
                status='active'
            )
            membership.status = 'inactive'
            membership.save()
            
            return Response({
                'success': True,
                'message': 'Left ministry successfully'
            })
        except MinistryMembership.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Not a member of this ministry'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def my_ministries(self, request):
        """
        Get current user's ministries.
        
        GET /api/v1/ministries/my-ministries/
        """
        if not hasattr(request.user, 'member_profile'):
            return Response({
                'success': True,
                'data': []
            })
        
        memberships = MinistryMembership.objects.filter(
            member=request.user.member_profile,
            status='active'
        )
        
        ministry_ids = memberships.values_list('ministry_id', flat=True)
        ministries = Ministry.objects.filter(id__in=ministry_ids)
        
        serializer = MinistrySerializer(ministries, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
