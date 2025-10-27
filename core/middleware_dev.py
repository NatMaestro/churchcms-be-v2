"""
Tenant selection middleware for Render deployment
Allows using ?tenant=subdomain when wildcard subdomains aren't available
"""
from django.db import connection
from apps.churches.models import Church
from django.conf import settings


class TenantQueryMiddleware:
    """
    Set tenant via query parameter when subdomain routing isn't available
    Usage: https://your-app.onrender.com/api/docs/?tenant=olamchurch
    
    Works in:
    - Development: localhost with ?tenant=
    - Render free tier: your-app.onrender.com?tenant=
    
    NOT needed in production with custom domain + wildcard DNS
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only use query param if subdomain routing failed
        # Check if we're on the base domain (no subdomain)
        host = request.get_host().split(':')[0]  # Remove port
        
        # Check if tenant query parameter is provided
        tenant_subdomain = request.GET.get('tenant')
        
        if tenant_subdomain and host in ['localhost', '127.0.0.1', 'faithflow-be.onrender.com']:
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

