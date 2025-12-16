"""
Member request views.
Handles public submissions and admin approval workflow.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.db import connection
from apps.churches.models import Church
from apps.authentication.models import User
from .models import MemberRequest, Member
from .serializers import (
    MemberRequestSerializer,
    MemberRequestListSerializer,
    MemberRequestPublicSerializer
)
from core.permissions import IsChurchAdmin


class MemberRequestViewSet(viewsets.ModelViewSet):
    """Member request management viewset (admin only)."""
    
    queryset = MemberRequest.objects.all()
    serializer_class = MemberRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsChurchAdmin]
    filterset_fields = ['status']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['submitted_at', 'status']
    
    def get_serializer_class(self):
        """Use simplified serializer for list views."""
        if self.action == 'list':
            return MemberRequestListSerializer
        return MemberRequestSerializer
    
    def get_queryset(self):
        """Filter requests by current tenant (church)."""
        # Get current tenant
        try:
            tenant = connection.get_tenant()
            if tenant and isinstance(tenant, Church):
                return MemberRequest.objects.filter(church=tenant)
        except:
            pass
        return MemberRequest.objects.none()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a member request (initial approval).
        Moves status from 'pending' to 'approved'.
        
        POST /api/v1/member-requests/:id/approve/
        """
        member_request = self.get_object()
        
        if member_request.status != 'pending':
            return Response({
                'success': False,
                'error': f'Request is already {member_request.status}. Only pending requests can be approved.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        member_request.status = 'approved'
        member_request.reviewed_by = request.user
        member_request.reviewed_at = timezone.now()
        member_request.save()
        
        return Response({
            'success': True,
            'message': 'Member request approved. Awaiting final confirmation.',
            'data': MemberRequestSerializer(member_request).data
        })
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirm a member request (final approval).
        Creates Member and User accounts.
        
        POST /api/v1/member-requests/:id/confirm/
        """
        member_request = self.get_object()
        
        if member_request.status != 'approved':
            return Response({
                'success': False,
                'error': f'Request must be approved before confirmation. Current status: {member_request.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if member_request.is_confirmed:
            return Response({
                'success': False,
                'error': 'Member account already created for this request.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # Get current tenant (church)
                tenant = connection.get_tenant()
                if not tenant or not isinstance(tenant, Church):
                    return Response({
                        'success': False,
                        'error': 'Could not determine church context'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Create User account
                user = User.objects.create_user(
                    email=member_request.email,
                    password=None,  # User will set password on first login
                    name=member_request.name,
                    church=tenant,
                    role='member',
                    is_active=True,
                    must_change_password=True  # Force password change on first login
                )
                
                # Create Member record
                # Split name into first_name and last_name
                name_parts = member_request.name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                member = Member.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    surname=last_name,  # For compatibility
                    email=member_request.email,
                    phone=member_request.phone,
                    address=member_request.address,
                    date_of_birth=member_request.date_of_birth,
                    gender=member_request.gender,
                    occupational_status=member_request.occupation or '',
                    membership_date=timezone.now().date(),
                    status='active',
                    notes=f"Created from member request. Reason: {member_request.reason_for_joining}"
                )
                
                # Update member request
                member_request.status = 'confirmed'
                member_request.confirmed_by = request.user
                member_request.confirmed_at = timezone.now()
                member_request.created_member = member
                member_request.created_user = user
                member_request.save()
                
                return Response({
                    'success': True,
                    'message': 'Member account created successfully. User can now log in.',
                    'data': {
                        'member_request': MemberRequestSerializer(member_request).data,
                        'member_id': member.id,
                        'user_id': user.id,
                        'login_email': user.email
                    }
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Failed to create member account: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a member request.
        
        POST /api/v1/member-requests/:id/reject/
        Body: { "reason": "optional rejection reason" }
        """
        member_request = self.get_object()
        
        if member_request.status == 'rejected':
            return Response({
                'success': False,
                'error': 'Request is already rejected.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if member_request.is_confirmed:
            return Response({
                'success': False,
                'error': 'Cannot reject a confirmed request. Member account already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        member_request.status = 'rejected'
        member_request.reviewed_by = request.user
        member_request.reviewed_at = timezone.now()
        member_request.rejection_reason = request.data.get('reason', '')
        member_request.save()
        
        return Response({
            'success': True,
            'message': 'Member request rejected.',
            'data': MemberRequestSerializer(member_request).data
        })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Public endpoint
def submit_member_request(request):
    """
    Public endpoint for submitting member requests.
    No authentication required.
    
    POST /api/v1/member-requests/submit/
    Body: {
        "subdomain": "churchsubdomain",
        "name": "...",
        "email": "...",
        ...
    }
    """
    serializer = MemberRequestPublicSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get church by subdomain
    subdomain = request.data.get('subdomain')
    if not subdomain:
        return Response({
            'success': False,
            'error': 'subdomain is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        church = Church.objects.get(subdomain=subdomain, is_active=True)
    except Church.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Church not found or inactive'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check for duplicate pending/approved requests
    existing = MemberRequest.objects.filter(
        email=serializer.validated_data['email'],
        church=church,
        status__in=['pending', 'approved']
    ).exists()
    
    if existing:
        return Response({
            'success': False,
            'error': 'You already have a pending or approved membership request for this church.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create member request
    member_request = MemberRequest.objects.create(
        church=church,
        **serializer.validated_data
    )
    
    return Response({
        'success': True,
        'message': 'Membership request submitted successfully. You will be notified once reviewed.',
        'data': {
            'id': member_request.id,
            'status': member_request.status,
            'submitted_at': member_request.submitted_at
        }
    }, status=status.HTTP_201_CREATED)



