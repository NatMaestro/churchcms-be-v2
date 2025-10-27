"""
Debug views for troubleshooting
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import connection


class DebugTenantView(APIView):
    """
    Debug endpoint to see tenant information
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Show current tenant and request info"""
        try:
            tenant = connection.tenant
            tenant_info = {
                'name': tenant.name if tenant else None,
                'schema': tenant.schema_name if tenant else None,
                'subdomain': tenant.subdomain if hasattr(tenant, 'subdomain') else None,
            }
        except:
            tenant_info = {'error': 'No tenant set'}
        
        return Response({
            'tenant': tenant_info,
            'host': request.get_host(),
            'path': request.path,
            'META_HTTP_HOST': request.META.get('HTTP_HOST'),
            'META_SERVER_NAME': request.META.get('SERVER_NAME'),
        })

