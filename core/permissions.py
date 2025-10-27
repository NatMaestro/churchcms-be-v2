"""
Custom permission classes for FaithFlow Studio.
"""

from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission to only allow super admins.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superadmin


class IsChurchAdmin(permissions.BasePermission):
    """
    Permission to only allow church admins.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_church_admin


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow read access to all, write access to admins only.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return request.user and request.user.is_authenticated and (
            request.user.is_superadmin or request.user.is_church_admin
        )


class IsMemberOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to allow members to access their own data, admins to access all.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admins can access all
        if request.user.is_church_admin or request.user.is_superadmin:
            return True
        
        # Members can only access their own data
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class TenantAccessPermission(permissions.BasePermission):
    """
    Permission to ensure users can only access data from their own church/tenant.
    """
    
    def has_object_permission(self, request, view, obj):
        # Super admins can access all
        if request.user.is_superadmin:
            return True
        
        # Check if object belongs to user's church
        if hasattr(obj, 'church'):
            return obj.church == request.user.church
        
        return True

