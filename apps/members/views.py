"""
Member views with export functionality.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Member, MemberWorkflow
from .serializers import (
    MemberSerializer,
    MemberListSerializer,
    MemberDetailSerializer,
    MemberWorkflowSerializer
)
from core.services import ExportService
from core.permissions import IsChurchAdmin, IsAdminOrReadOnly


class MemberViewSet(viewsets.ModelViewSet):
    """Member management viewset."""
    
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]
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
        """Filter members by current tenant."""
        # Members are tenant-specific (in tenant schema)
        return Member.objects.all()
    
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
