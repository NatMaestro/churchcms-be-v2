"""
Tenant selection middleware using X-Tenant-Subdomain header.
This middleware reads the tenant subdomain from the X-Tenant-Subdomain header
and sets the appropriate tenant schema for the request.
"""
from django.db import connection
from django.http import JsonResponse
from apps.churches.models import Church
from django_tenants.utils import get_public_schema_name
import logging

logger = logging.getLogger(__name__)


class TenantHeaderMiddleware:
    """
    Set tenant via X-Tenant-Subdomain header.
    
    Security:
    - Validates tenant exists before setting
    - Falls back to public schema if tenant not found
    - Public routes (registration, login) can work without tenant header
    
    Usage:
    - Frontend sends: X-Tenant-Subdomain: apostolicchurch
    - Middleware sets tenant schema for that request
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get tenant subdomain from header
        tenant_subdomain = request.headers.get('X-Tenant-Subdomain', '').strip()
        print(f"Tenant subdomain: {tenant_subdomain}")
        # Public routes that don't require tenant (registration, login, health checks, webhooks)
        public_paths = [
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/auth/refresh/',
            '/api/v1/auth/forgot-password/',
            '/api/v1/auth/reset-password/',
            '/api/v1/churches/subscription-payment/webhook/',  # Paystack webhook (no tenant needed)
            '/health/',
            '/api/docs/',
            '/api/schema/',
        ]
        
        # Check if this is a public route
        is_public_route = any(request.path.startswith(path) for path in public_paths)
        
        # If no tenant header and not a public route, stay in public schema
        if not tenant_subdomain:
            if not is_public_route:
                logger.warning(f'⚠️ No X-Tenant-Subdomain header for protected route: {request.path}')
            response = self.get_response(request)
            return response
        
        # Validate and set tenant
        try:
            # Ensure we're in public schema to query Church model
            connection.set_schema_to_public()
            
            # Get church by subdomain (from public schema)
            church = Church.objects.get(subdomain=tenant_subdomain)
            
            # Security: Check if church is active
            if not church.is_active:
                logger.warning(f'⚠️ Inactive church subdomain attempted: {tenant_subdomain}')
                response = self.get_response(request)
                return response
            
            # Set the tenant for this request
            connection.set_tenant(church)
            
            # Store in request for easy access in views
            request.tenant = church
            request.church = church
            request.church_id = church.id
            
            logger.debug(f'✅ Tenant set: {tenant_subdomain} (schema: {church.schema_name})')
            
        except Church.DoesNotExist:
            # Tenant not found - stay in public schema
            logger.warning(f'⚠️ Church not found for subdomain: {tenant_subdomain}')
            connection.set_schema_to_public()
            
        except Exception as e:
            # On any error, reset to public schema for safety
            logger.error(f'❌ Error setting tenant: {e}')
            connection.set_schema_to_public()
        
        response = self.get_response(request)
        return response

