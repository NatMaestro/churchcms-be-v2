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
        # Get hostname without port
        host = request.get_host().split(':')[0]
        
        # Extract tenant subdomain from Render hostname format: subdomain.faithflow-be.onrender.com
        tenant_subdomain = None
        
        # Check if we're on Render free tier domain
        if host.endswith('faithflow-be.onrender.com'):
            # Extract subdomain if present (e.g., "apostolicchurch" from "apostolicchurch.faithflow-be.onrender.com")
            if host != 'faithflow-be.onrender.com':
                # Has subdomain: extract it
                tenant_subdomain = host.replace('.faithflow-be.onrender.com', '')
            # else: No subdomain, treat as public domain (tenant_subdomain remains None)
        
        # Fallback: Check query parameter (for localhost or when subdomain extraction fails)
        if not tenant_subdomain:
            tenant_subdomain = request.GET.get('tenant')
            # Only use query param on specific hosts
            if tenant_subdomain and host not in ['localhost', '127.0.0.1', 'faithflow-be.onrender.com']:
                tenant_subdomain = None
        
        # Set tenant if subdomain found
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

