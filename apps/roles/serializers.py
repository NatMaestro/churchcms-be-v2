"""
Role and permission serializers.
"""

from rest_framework import serializers
from .models import Role, Permission, UserRole


class PermissionSerializer(serializers.ModelSerializer):
    """Permission serializer."""
    
    class Meta:
        model = Permission
        fields = [
            'id', 'name', 'code', 'resource', 'action', 'description',
            'is_system_permission', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RoleSerializer(serializers.ModelSerializer):
    """Role serializer."""
    
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'permissions', 'color', 'icon',
            'is_default', 'is_system_role', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRoleSerializer(serializers.ModelSerializer):
    """User role serializer."""
    
    user_name = serializers.CharField(source='user.name', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.name', read_only=True)
    
    class Meta:
        model = UserRole
        fields = [
            'id', 'user', 'user_name', 'role', 'role_name', 'assigned_by',
            'assigned_by_name', 'assigned_at', 'is_active', 'expires_at'
        ]
        read_only_fields = ['id', 'assigned_at']

