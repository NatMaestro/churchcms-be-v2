"""
Service request views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import ServiceRequest
from .serializers import ServiceRequestSerializer, ServiceRequestListSerializer
from core.permissions import IsAdminOrReadOnly


class ServiceRequestViewSet(viewsets.ModelViewSet):
    """Service request management viewset."""
    
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['type', 'status', 'priority']
    search_fields = ['title', 'description', 'member__first_name', 'member__last_name']
    ordering_fields = ['created_at', 'priority', 'status']
    
    def get_serializer_class(self):
        """Use simplified serializer for list views."""
        if self.action == 'list':
            return ServiceRequestListSerializer
        return ServiceRequestSerializer
    
    def get_queryset(self):
        """Filter requests."""
        user = self.request.user
        if user.is_church_admin or user.is_superadmin:
            return ServiceRequest.objects.all()
        # Members see only their requests
        if hasattr(user, 'member_profile'):
            return ServiceRequest.objects.filter(member=user.member_profile)
        return ServiceRequest.objects.none()
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Get pending service requests.
        
        GET /api/v1/service-requests/pending/
        """
        pending_requests = self.get_queryset().filter(status='pending')
        serializer = ServiceRequestListSerializer(pending_requests, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a service request.
        
        POST /api/v1/service-requests/:id/approve/
        """
        if not (request.user.is_church_admin or request.user.is_superadmin):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        service_request = self.get_object()
        service_request.status = 'approved'
        service_request.save()
        
        return Response({
            'success': True,
            'message': 'Request approved successfully'
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a service request.
        
        POST /api/v1/service-requests/:id/reject/
        """
        if not (request.user.is_church_admin or request.user.is_superadmin):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        service_request = self.get_object()
        service_request.status = 'rejected'
        service_request.admin_notes = request.data.get('notes', '')
        service_request.save()
        
        return Response({
            'success': True,
            'message': 'Request rejected'
        })
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark service request as completed.
        
        POST /api/v1/service-requests/:id/complete/
        """
        if not (request.user.is_church_admin or request.user.is_superadmin):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        service_request = self.get_object()
        service_request.status = 'completed'
        service_request.completed_at = timezone.now()
        service_request.save()
        
        return Response({
            'success': True,
            'message': 'Request marked as completed'
        })
