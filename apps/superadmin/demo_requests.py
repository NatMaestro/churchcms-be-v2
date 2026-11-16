"""
Public "Book a demo" form and the email that tells platform admins about it.

Unauthenticated, so it is throttled per IP and has a honeypot field that real
people never fill in. The email names only the person and the church; phone,
email and message stay in the platform admin.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import permissions, serializers, status
from rest_framework.decorators import (api_view, authentication_classes, permission_classes,
                                       throttle_classes)
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.authentication.models import User
from core.frontend_links import frontend_url

from .models import DemoRequest, purge_stale_demo_requests

logger = logging.getLogger(__name__)

PLATFORM_DEMO_REQUESTS_PATH = '/superadmin/demo-requests'
HONEYPOT_FIELD = 'website'
THANK_YOU_MESSAGE = "Thank you! We'll contact you shortly to arrange your demo."


class DemoRequestThrottle(AnonRateThrottle):
    scope = 'demo_request_submit'


class DemoRequestFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoRequest
        fields = ['name', 'role', 'phone', 'email', 'church_name', 'congregation_size',
                  'preferred_time', 'message']

    def validate(self, attrs):
        return {key: value.strip() if isinstance(value, str) else value for key, value in attrs.items()}


def email_platform_admins(demo_request):
    admins = User.objects.filter(role='superadmin', is_active=True)
    link = frontend_url(PLATFORM_DEMO_REQUESTS_PATH)
    for admin in admins:
        try:
            send_mail(
                subject=f'Demo request from {demo_request.church_name}',
                message=(
                    f"Hello {admin.name},\n\n"
                    f"{demo_request.name} from {demo_request.church_name} would like a {settings.PLATFORM_NAME} demo.\n\n"
                    f"See their details and follow up:\n{link}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
            )
        except Exception:
            logger.exception('demo_request_admin_email_failed',
                             extra={'demo_request_id': demo_request.pk, 'admin_id': admin.pk})


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])  # public form on the landing page
@throttle_classes([DemoRequestThrottle])
def submit_demo_request(request):
    """POST /api/v1/demo-requests/ {name, role?, phone, email, church_name, congregation_size, preferred_time?, message?}"""
    if request.data.get(HONEYPOT_FIELD):
        # Looks like a bot. Answer as if it worked so it learns nothing.
        logger.info('demo_request_honeypot')
        return Response({'success': True, 'message': THANK_YOU_MESSAGE}, status=status.HTTP_201_CREATED)

    form = DemoRequestFormSerializer(data=request.data)
    if not form.is_valid():
        return Response({'success': False, 'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

    demo_request = form.save()
    logger.info('demo_request_received', extra={'demo_request_id': demo_request.pk})
    email_platform_admins(demo_request)
    purged = purge_stale_demo_requests()
    if purged:
        logger.info('demo_requests_purged', extra={'count': purged})
    return Response({'success': True, 'message': THANK_YOU_MESSAGE}, status=status.HTTP_201_CREATED)
