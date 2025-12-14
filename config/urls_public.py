"""
Public schema URLs (non-tenant specific).
Handles church registration, super admin, and public landing pages.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.churches.views_setup import InitialSetupView

def api_root(request):
    """Root API endpoint - returns available endpoints."""
    return JsonResponse({
        'message': 'FaithFlow Studio API',
        'version': 'v1',
        'endpoints': {
            'auth': '/api/v1/auth/',
            'docs': '/api/docs/',
            'admin': '/admin/',
        },
        'public_endpoints': [
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/auth/refresh/',
        ]
    })

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API Root
    path('api/v1/', api_root, name='api-root'),
    
    # Initial setup endpoint (for deployment without shell access)
    path('api/v1/setup/initial/', InitialSetupView.as_view(), name='initial-setup'),
    
    # Public authentication (church registration)
    path('api/v1/auth/', include('apps.authentication.urls_public')),
    
    # Public member request submission (no auth required)
    path('api/v1/member-requests/', include('apps.members.urls_public')),
    
    # Super admin endpoints
    path('api/v1/superadmin/', include('apps.superadmin.urls')),
]

