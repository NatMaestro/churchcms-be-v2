"""
Service request views.

Church staff see every request (with the member's contact details) and
manage them: status, reply (admin_notes), assignment. A member sees only their
own requests, submits as themselves (the member comes from the login), and can
cancel a request while it is still pending. See core.member_context.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from core.member_context import is_church_staff, member_for
from .models import ServiceRequest
from .serializers import (
    MemberServiceRequestSerializer,
    ServiceRequestListSerializer,
    ServiceRequestSerializer,
)

STAFF_ONLY_ACTIONS = ('update', 'partial_update', 'destroy', 'approve', 'reject', 'complete')


class IsChurchStaff(permissions.BasePermission):
    message = 'Only church staff can change service requests.'

    def has_permission(self, request, view):
        return is_church_staff(request.user)


class ServiceRequestViewSet(viewsets.ModelViewSet):
    """Service request management viewset."""

    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['type', 'status', 'priority']
    search_fields = ['title', 'description', 'member__first_name', 'member__last_name']
    ordering_fields = ['created_at', 'priority', 'status']

    def _viewer(self):
        """The signed-in person's member record in this church (cached per request)."""
        if not hasattr(self, '_viewer_member'):
            self._viewer_member = member_for(self.request.user)
        return self._viewer_member

    def get_permissions(self):
        if self.action in STAFF_ONLY_ACTIONS:
            return [permissions.IsAuthenticated(), IsChurchStaff()]
        return super().get_permissions()

    def get_serializer_class(self):
        """Staff get the full record; members see their own without contact details."""
        if is_church_staff(self.request.user):
            return ServiceRequestListSerializer if self.action == 'list' else ServiceRequestSerializer
        if self.action == 'create':
            return MemberServiceRequestSerializer
        return ServiceRequestListSerializer

    def get_queryset(self):
        """Staff: every request. Members: only their own."""
        requests = ServiceRequest.objects.select_related('member')
        if is_church_staff(self.request.user):
            return requests
        viewer = self._viewer()
        return requests.filter(member=viewer) if viewer else requests.none()

    def create(self, request, *args, **kwargs):
        if not is_church_staff(request.user) and self._viewer() is None:
            return Response({
                'success': False,
                'error': 'No member record is linked to this account.'
            }, status=status.HTTP_400_BAD_REQUEST)
        response = super().create(request, *args, **kwargs)
        if not is_church_staff(request.user):
            # Answer with the member view of the saved request.
            response.data = ServiceRequestListSerializer(self._saved).data
        return response

    def perform_create(self, serializer):
        """A member's request is always their own and starts as pending; staff may record one for anyone."""
        if is_church_staff(self.request.user):
            self._saved = serializer.save()
        else:
            self._saved = serializer.save(member=self._viewer(), status='pending')

    def perform_update(self, serializer):
        """Stamp completed_at when staff mark a request completed."""
        instance = serializer.save()
        if instance.status == 'completed' and instance.completed_at is None:
            instance.completed_at = timezone.now()
            instance.save(update_fields=['completed_at'])

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
    def cancel(self, request, pk=None):
        """
        Cancel a request that is still pending (the member who asked, or staff).

        POST /api/v1/service-requests/:id/cancel/
        """
        service_request = self.get_object()  # members only reach their own
        if service_request.status != 'pending':
            return Response({
                'success': False,
                'error': 'Only a request that is still pending can be cancelled.'
            }, status=status.HTTP_400_BAD_REQUEST)
        service_request.status = 'cancelled'
        service_request.save(update_fields=['status', 'updated_at'])
        return Response(ServiceRequestListSerializer(service_request).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a service request.

        POST /api/v1/service-requests/:id/approve/
        """
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
        service_request = self.get_object()
        service_request.status = 'completed'
        service_request.completed_at = timezone.now()
        service_request.save()

        return Response({
            'success': True,
            'message': 'Request marked as completed'
        })
