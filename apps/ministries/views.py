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
from django.db import transaction
from django.db.models import Exists, OuterRef

from core.member_context import acting_member
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
    
    def get_permissions(self):
        """Any signed-in church user may join or leave; changing ministries stays with admins."""
        if self.action in ('join', 'leave'):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        """Active ministries, each marked with whether the signed-in person belongs to it."""
        my_membership = MinistryMembership.objects.filter(
            ministry=OuterRef('pk'), member__user=self.request.user, status='active',
        )
        return Ministry.objects.filter(is_active=True).annotate(is_member=Exists(my_membership)).order_by('name')
    
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
        member = acting_member(request)
        
        if member is None:
            return Response({
                'success': False,
                'error': 'No member record found to join with.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Lock the ministry so two joins cannot both take the last place.
            ministry = Ministry.objects.select_for_update().get(pk=ministry.pk)
            membership = MinistryMembership.objects.filter(ministry=ministry, member=member).first()
            if membership and membership.status == 'active':
                return Response({
                    'success': False,
                    'error': 'Already a member of this ministry'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check capacity
            if ministry.max_capacity:
                current_members = ministry.members.filter(ministrymembership__status='active').count()
                if current_members >= ministry.max_capacity:
                    return Response({
                        'success': False,
                        'error': 'Ministry is at capacity'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            if membership:  # rejoining after leaving
                membership.status = 'active'
                membership.save(update_fields=['status'])
            else:
                membership = MinistryMembership.objects.create(
                    ministry=ministry, member=member, status='active', role='member',
                )
        
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
        member = acting_member(request)
        
        try:
            membership = MinistryMembership.objects.get(
                ministry=ministry,
                member=member,
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
