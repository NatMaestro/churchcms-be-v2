"""
Main URL configuration for FaithFlow Studio Backend.
This is the public schema URLs (for non-tenant requests).
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.admin),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Public API (church registration, super admin)
    path('api/v1/', include('apps.authentication.urls_public')),
    path('api/v1/superadmin/', include('apps.superadmin.urls')),
]
