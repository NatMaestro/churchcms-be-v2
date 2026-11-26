"""
Member views with export functionality.
"""

import logging

from django.db import connection, transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.authentication.models import User
from apps.churches.models import Church
from .member_request_notifications import send_member_invite
from .models import Member, MemberWorkflow
from .serializers import (
    MemberSerializer,
    MemberListSerializer,
    MemberDetailSerializer,
    MemberWorkflowSerializer
)
from core.services import ExportService
from core.member_context import is_church_staff, member_for
from core.permissions import IsChurchAdmin, IsChurchAdminOrSuperAdmin, IsAdminOrReadOnly

logger = logging.getLogger(__name__)


class MemberViewSet(viewsets.ModelViewSet):
    """
    Member management viewset.
    Church staff see and change every member; a member can only read their
    own record (see core.member_context).
    """
    
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['status', 'gender']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'member_id']
    ordering_fields = ['created_at', 'last_name', 'membership_date']
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action."""
        if self.action == 'list':
            return MemberListSerializer
        elif self.action == 'retrieve':
            return MemberDetailSerializer
        return MemberSerializer
    
    def get_queryset(self):
        """Members are tenant-specific (in tenant schema); members see only themselves."""
        if is_church_staff(self.request.user):
            return Member.objects.all()
        return Member.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        The signed-in person's own member record.

        GET /api/v1/members/me/  ->  member detail, or 404 if this login has no member record.
        """
        member = member_for(request.user)
        if member is None:
            return Response({
                'success': False,
                'error': 'No member record is linked to this account.'
            }, status=status.HTTP_404_NOT_FOUND)
        return Response(MemberDetailSerializer(member, context=self.get_serializer_context()).data)
    
    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, IsChurchAdminOrSuperAdmin])
    def invite(self, request, pk=None):
        """
        Give a member their login: create it with no usable password, link it to
        the member, and email a single-use link to set the password. Calling it
        again emails a fresh link (earlier links stop working) until the member
        has set a password.

        POST /api/v1/members/:id/invite/
        """
        member = self.get_object()
        church = connection.get_tenant()
        if not isinstance(church, Church):
            return Response({'success': False, 'error': 'Could not determine church context'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not member.email:
            return Response({'success': False, 'error': 'Add an email address for this member first.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = member.user
        created = user is None
        if created:
            # Logins are global (one church per account), as in member-request confirm.
            if User.objects.filter(email__iexact=member.email).exists():
                return Response({
                    'success': False,
                    'error': 'This email already has an account, so a new member login cannot be created for it.'
                }, status=status.HTTP_409_CONFLICT)
            with transaction.atomic():
                user = User.objects.create_user(
                    email=member.email,
                    password=None,  # Unusable until they set one via the emailed invite link
                    name=member.full_name.strip() or member.email,
                    church=church,
                    role='member',
                    is_active=True,
                    must_change_password=True,
                )
                member.user = user
                member.save(update_fields=['user'])
        elif user.has_usable_password():
            return Response({
                'success': False,
                'error': 'This member has already set a password. They can use "Forgot password" if needed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        elif not user.is_active:
            return Response({'success': False, 'error': "This member's login is switched off."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Sent only after the login is committed; a failed email leaves it in
        # place and the admin can call this again.
        invite_sent = send_member_invite(user, church, intro=f"{church.name} has added you as a member.")
        if not created and not invite_sent:
            return Response({'success': False, 'error': 'The invite email could not be sent. Please try again later.'},
                            status=status.HTTP_502_BAD_GATEWAY)
        if invite_sent:
            message = 'An invite to set their password has been emailed.'
        else:
            message = 'The login was created, but the invite email could not be sent. Try sending it again.'
        logger.info('member_invite', extra={'member_id': member.pk, 'user_id': user.pk,
                                            'login_created': created, 'invite_sent': invite_sent})
        return Response({
            'success': True,
            'message': message,
            'data': {'user_id': user.pk, 'login_email': user.email, 'invite_sent': invite_sent},
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """
        Export members to CSV.
        
        GET /api/v1/members/export-csv/?status=active
        """
        # Check permissions
        if not (request.user.is_church_admin or request.user.is_superadmin):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get filtered queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        # Export
        church_name = request.user.church.name if request.user.church else None
        return ExportService.export_members_csv(queryset, church_name)
    
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """
        Export members to Excel.
        
        GET /api/v1/members/export-excel/?status=active
        """
        # Check permissions
        if not (request.user.is_church_admin or request.user.is_superadmin):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get filtered queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        # Export
        church_name = request.user.church.name if request.user.church else None
        return ExportService.export_members_excel(queryset, church_name)
    
    @action(detail=False, methods=['post'])
    def import_members(self, request):
        """
        Import members from CSV.
        
        POST /api/v1/members/import/
        """
        # TODO: Implement CSV import
        return Response({
            'success': False,
            'error': 'Not implemented yet'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    @action(detail=True, methods=['get'])
    def sacraments(self, request, pk=None):
        """
        Get member sacraments.
        
        GET /api/v1/members/:id/sacraments/
        """
        member = self.get_object()
        return Response({
            'success': True,
            'sacraments': member.sacraments
        })
    
    @action(detail=True, methods=['put'])
    def update_sacraments(self, request, pk=None):
        """
        Update member sacraments.
        
        PUT /api/v1/members/:id/update-sacraments/
        """
        member = self.get_object()
        sacrament_data = request.data.get('sacraments', {})
        
        # Merge with existing sacraments
        member.sacraments = {**member.sacraments, **sacrament_data}
        member.save()
        
        return Response({
            'success': True,
            'message': 'Sacraments updated successfully',
            'sacraments': member.sacraments
        })
