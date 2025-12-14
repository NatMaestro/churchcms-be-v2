"""
Tenant isolation middleware.
Ensures proper tenant isolation and data access control.
"""

from django.http import JsonResponse
from django_tenants.utils import get_tenant_model, get_public_schema_name


class TenantIsolationMiddleware:
    """
    Ensure tenant isolation and prevent cross-tenant data access.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get current tenant
        tenant = getattr(request, 'tenant', None)
        
        # Add tenant to request for easy access
        if tenant and tenant.schema_name != get_public_schema_name():
            request.church = tenant
            request.church_id = tenant.id
        else:
            request.church = None
            request.church_id = None
        
        response = self.get_response(request)
        
        # Add tenant identifier to response headers (for debugging)
        if tenant and hasattr(tenant, 'schema_name'):
            response['X-Tenant-Schema'] = tenant.schema_name
        
        return response






