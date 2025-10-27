"""
Role and permission views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Role, Permission, UserRole
from .serializers import (
    RoleSerializer,
    PermissionSerializer,
    UserRoleSerializer
)
from core.permissions import IsChurchAdmin


class RoleViewSet(viewsets.ModelViewSet):
    """Role management viewset."""
    
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsChurchAdmin]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    
    def get_queryset(self):
        """Filter roles."""
        return Role.objects.all().order_by('name')
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """
        Clone a role.
        
        POST /api/v1/roles/:id/clone/
        Body: { "name": "New Role Name" }
        """
        role = self.get_object()
        new_name = request.data.get('name')
        
        if not new_name:
            return Response({
                'success': False,
                'error': 'Name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create cloned role
        new_role = Role.objects.create(
            name=new_name,
            description=f"Cloned from {role.name}",
            permissions=role.permissions,
            color=role.color,
            icon=role.icon,
            is_default=False,
            is_system_role=False
        )
        
        return Response({
            'success': True,
            'message': 'Role cloned successfully',
            'role': RoleSerializer(new_role).data
        })


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Permission management viewset (read-only for non-superadmins)."""
    
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['resource', 'action']
    ordering_fields = ['resource', 'action']


class UserRoleViewSet(viewsets.ModelViewSet):
    """User role assignment viewset."""
    
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsChurchAdmin]
    filterset_fields = ['user', 'role', 'is_active']
    
    def get_queryset(self):
        """Filter user roles."""
        return UserRole.objects.all().order_by('-assigned_at')
    
    def perform_create(self, serializer):
        """Set assigned_by to current user."""
        serializer.save(assigned_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def assign(self, request):
        """
        Assign role to user.
        
        POST /api/v1/user-roles/assign/
        Body: { "user_id": "xxx", "role_id": "xxx" }
        """
        user_id = request.data.get('user_id')
        role_id = request.data.get('role_id')
        
        if not user_id or not role_id:
            return Response({
                'success': False,
                'error': 'user_id and role_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user role
        user_role, created = UserRole.objects.get_or_create(
            user_id=user_id,
            role_id=role_id,
            defaults={'assigned_by': request.user, 'is_active': True}
        )
        
        if not created:
            return Response({
                'success': False,
                'error': 'Role already assigned to user'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': 'Role assigned successfully',
            'user_role': UserRoleSerializer(user_role).data
        })
