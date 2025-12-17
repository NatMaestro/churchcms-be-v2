"""
Tenant isolation middleware.
Ensures proper tenant isolation and data access control.
"""

from django.http import JsonResponse
from django_tenants.utils import get_tenant_model, get_public_schema_name
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware:
    """
    Ensure tenant isolation and prevent cross-tenant data access.
    
    Security features:
    - Validates authenticated users belong to the tenant they're accessing
    - Prevents cross-tenant data access
    - Handles public routes that don't require tenant
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get current tenant
        tenant = getattr(request, 'tenant', None)
        
        # Public routes that don't require tenant validation
        public_paths = [
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/auth/refresh/',
            '/api/v1/auth/forgot-password/',
            '/api/v1/auth/reset-password/',
            '/health/',
            '/api/docs/',
            '/api/schema/',
        ]
        
        is_public_route = any(request.path.startswith(path) for path in public_paths)
        
        # Add tenant to request for easy access
        if tenant and tenant.schema_name != get_public_schema_name():
            request.church = tenant
            request.church_id = tenant.id
            
            # Security: Validate authenticated users belong to this tenant
            # (Skip for public routes and unauthenticated requests)
            if not is_public_route and hasattr(request, 'user') and request.user.is_authenticated:
                user_church_id = getattr(request.user, 'church_id', None)
                
                # Check if user's church matches the tenant
                if user_church_id and user_church_id != tenant.id:
                    logger.warning(
                        f'🚫 Security: User {request.user.id} attempted to access tenant {tenant.id} '
                        f'but belongs to church {user_church_id}'
                    )
                    return JsonResponse(
                        {
                            'error': 'Access denied',
                            'detail': 'You do not have permission to access this church\'s data.'
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
        else:
            request.church = None
            request.church_id = None
        
        response = self.get_response(request)
        
        # Add tenant identifier to response headers (for debugging)
        if tenant and hasattr(tenant, 'schema_name'):
            response['X-Tenant-Schema'] = tenant.schema_name
        
        return response






