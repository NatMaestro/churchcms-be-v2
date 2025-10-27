"""
Public schema URLs (non-tenant specific).
Handles church registration, super admin, and public landing pages.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.churches.views_setup import InitialSetupView

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Initial setup endpoint (for deployment without shell access)
    path('api/v1/setup/initial/', InitialSetupView.as_view(), name='initial-setup'),
    
    # Public authentication (church registration)
    path('api/v1/auth/', include('apps.authentication.urls_public')),
    
    # Super admin endpoints
    path('api/v1/superadmin/', include('apps.superadmin.urls')),
]

