"""
Member request views.
Handles public submissions and admin approval workflow.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.db import connection
from django_tenants.utils import tenant_context
from apps.churches.models import Church
from apps.authentication.models import User
from .models import MemberRequest, Member
from .serializers import (
    MemberRequestSerializer,
    MemberRequestListSerializer,
    MemberRequestPublicSerializer
)
from core.permissions import IsChurchAdmin
from .member_request_notifications import email_admins_of_new_request, send_member_invite
import logging

logger = logging.getLogger(__name__)


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
        
        tenant = connection.get_tenant()
        if not tenant or not isinstance(tenant, Church):
            return Response({
                'success': False,
                'error': 'Could not determine church context'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Logins are global (one church per account), so an email that already
        # has an account cannot be given a second one here.
        if User.objects.filter(email__iexact=member_request.email).exists():
            return Response({
                'success': False,
                'error': 'This email already has an account, so a new member login cannot be created for it.'
            }, status=status.HTTP_409_CONFLICT)

        try:
            with transaction.atomic():
                # Create User account
                user = User.objects.create_user(
                    email=member_request.email,
                    password=None,  # Unusable until they set one via the emailed invite link
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
        except Exception:
            logger.exception('member_request_confirm_failed', extra={'member_request_id': member_request.pk})
            return Response({
                'success': False,
                'error': 'Failed to create member account.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Sent only after the account is committed; a failed email leaves the
        # account in place and the admin can use resend-invite.
        invite_sent = send_member_invite(user, tenant)
        if invite_sent:
            message = 'Member account created. An invite to set their password has been emailed.'
        else:
            message = 'Member account created, but the invite email could not be sent. Use Resend invite to try again.'

        return Response({
            'success': True,
            'message': message,
            'data': {
                'member_request': MemberRequestSerializer(member_request).data,
                'member_id': member.id,
                'user_id': user.id,
                'login_email': user.email,
                'invite_sent': invite_sent,
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='resend-invite')
    def resend_invite(self, request, pk=None):
        """
        Email a fresh invite link to a confirmed member who has not yet set a
        password. Any earlier link stops working.

        POST /api/v1/members/requests/:id/resend-invite/
        """
        member_request = self.get_object()
        user = member_request.created_user

        if member_request.status != 'confirmed' or user is None or not user.is_active:
            return Response({
                'success': False,
                'error': 'Only confirmed requests with an active member account can be sent an invite.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if user.has_usable_password():
            return Response({
                'success': False,
                'error': 'This member has already set a password. They can use "Forgot password" if needed.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not send_member_invite(user, connection.get_tenant()):
            return Response({
                'success': False,
                'error': 'The invite email could not be sent. Please try again later.'
            }, status=status.HTTP_502_BAD_GATEWAY)

        return Response({'success': True, 'message': 'Invite sent.'})
    
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


class MemberRequestSubmitThrottle(AnonRateThrottle):
    """Per-IP limit on public membership applications (rate set in settings)."""

    scope = 'member_request_submit'


MEMBER_REQUEST_SUBMITTED_MESSAGE = (
    'Membership request submitted successfully. You will be notified once reviewed.'
)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Public endpoint
@throttle_classes([AnonRateThrottle, MemberRequestSubmitThrottle])
def submit_member_request(request):
    """
    Public endpoint for submitting member requests.
    No authentication required.

    POST /api/v1/members/member-requests/submit/
    Body: {
        "subdomain": "churchsubdomain",
        "name": "...",
        "email": "...",
        ...
    }

    A repeat application from an email that already has a pending or approved
    request gets the same response as a new one and creates nothing, so the
    endpoint cannot be used to find out who has applied.
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

    # MemberRequest lives in the church's own schema; the request arrives
    # without a tenant header, so switch to that schema explicitly.
    with tenant_context(church):
        already_applied = MemberRequest.objects.filter(
            email__iexact=serializer.validated_data['email'],
            church=church,
            status__in=['pending', 'approved']
        ).exists()

        if not already_applied:
            member_request = MemberRequest.objects.create(
                church=church,
                **serializer.validated_data
            )
            email_admins_of_new_request(church, member_request)

    return Response({
        'success': True,
        'message': MEMBER_REQUEST_SUBMITTED_MESSAGE,
    }, status=status.HTTP_201_CREATED)



