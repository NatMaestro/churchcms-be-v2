"""
Tenant-specific URLs.
These URLs are available within each church's subdomain.
"""

from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.churches.views_debug import DebugTenantView

urlpatterns = [
    # Debug endpoint (remove in production)
    path('debug/tenant/', DebugTenantView.as_view(), name='debug-tenant'),
    
    # API Documentation (per tenant)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Authentication endpoints (login, logout, etc.)
    path('api/v1/auth/', include('apps.authentication.urls')),
    
    # Church management
    path('api/v1/churches/', include('apps.churches.urls')),
    
    # Member management
    path('api/v1/members/', include('apps.members.urls')),
    
    # Events
    path('api/v1/events/', include('apps.events.urls')),
    
    # Payments & Giving
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/giving/', include('apps.payments.urls_giving')),
    
    # Ministries & Small Groups
    path('api/v1/ministries/', include('apps.ministries.urls')),
    
    # Volunteer Opportunities
    path('api/v1/volunteer-opportunities/', include('apps.volunteers.urls')),
    path('api/v1/volunteer-signups/', include('apps.volunteers.urls_signups')),
    path('api/v1/volunteer-hours/', include('apps.volunteers.urls_hours')),
    
    # Service Requests
    path('api/v1/service-requests/', include('apps.requests.urls')),
    path('api/v1/requests/', include('apps.requests.urls')),  # Alias
    
    # Prayer Requests
    path('api/v1/prayer-requests/', include('apps.prayers.urls')),
    
    # Altar Calls
    path('api/v1/altar-calls/', include('apps.altarcalls.urls')),
    
    # Announcements
    path('api/v1/announcements/', include('apps.announcements.urls')),
    
    # Notifications
    path('api/v1/notifications/', include('apps.notifications.urls')),
    
    # Roles & Permissions
    path('api/v1/roles/', include('apps.roles.urls')),
    path('api/v1/permissions/', include('apps.roles.urls_permissions')),
    path('api/v1/user-roles/', include('apps.roles.urls_user_roles')),
    
    # Themes
    path('api/v1/themes/', include('apps.themes.urls')),
    
    # Documents
    path('api/v1/documents/', include('apps.documents.urls')),
    
    # Dashboard & Analytics
    path('api/v1/dashboard/', include('apps.analytics.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls_analytics')),
    path('api/v1/reports/', include('apps.analytics.urls_reports')),
]

