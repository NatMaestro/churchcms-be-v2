"""
Public, read-only platform settings for the website and church Billing page:
how churches contact Faithflow360. Edited in the platform admin.
"""
from rest_framework import permissions
from rest_framework.decorators import (api_view, authentication_classes, permission_classes,
                                       throttle_classes)
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import PlatformSettings

SITE_SETTINGS_VERSION = 1


class SiteSettingsThrottle(AnonRateThrottle):
    scope = 'site_settings'


@api_view(['GET'])
@authentication_classes([])  # public: a stale login cookie must not turn this into a 401
@permission_classes([permissions.AllowAny])
@throttle_classes([SiteSettingsThrottle])
def public_site_settings(request):
    """GET /api/v1/site-settings/ -> {"version": 1, "whatsapp_number": "...", "contact_email": "..."}"""
    current = PlatformSettings.load()
    return Response({
        'version': SITE_SETTINGS_VERSION,
        'whatsapp_number': current.whatsapp_number,
        'contact_email': current.contact_email,
    })
