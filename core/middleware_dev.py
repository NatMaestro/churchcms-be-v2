"""
Development middleware for easier tenant testing
Allows using ?tenant=subdomain in development
"""
from django.db import connection
from apps.churches.models import Church


class DevTenantMiddleware:
    """
    Development middleware to set tenant via query parameter
    Usage: http://localhost:8000/api/docs/?tenant=testchurch
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if tenant query parameter is provided
        tenant_subdomain = request.GET.get('tenant')
        
        if tenant_subdomain:
            try:
                # Get church by subdomain
                church = Church.objects.get(subdomain=tenant_subdomain)
                # Set the tenant for this request
                connection.set_tenant(church)
                # Store in request for later use
                request.tenant = church
            except Church.DoesNotExist:
                pass  # Let the main tenant middleware handle it
        
        response = self.get_response(request)
        return response

