import logging

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT auth that prefers HttpOnly cookies and falls back to the Authorization header.
    This keeps browser clients on cookie-based auth to avoid localStorage token storage.

    Tenant binding: the tenant for a request comes from the client-supplied
    X-Tenant-Subdomain header (core.middleware_dev.TenantHeaderMiddleware), so a
    valid token alone proves nothing about which church's data the caller may
    see. A token is only accepted when its user belongs to the request's tenant
    (superadmins excepted). Otherwise the request is treated as anonymous, so
    protected endpoints fail closed with 401 while public ones keep working.

    This is the single enforcement point because every DRF view uses this class
    (no view overrides authentication_classes). TenantIsolationMiddleware cannot
    do this check: it runs before DRF has decoded the token.
    """

    def authenticate(self, request):
        # First try standard Authorization header
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = None

        # If no header token, try cookie
        if raw_token is None:
            raw_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        if not user_may_access_tenant(user, getattr(request, 'tenant', None)):
            logger.warning(
                'tenant_binding_rejected',
                extra={
                    'user_id': user.pk,
                    'user_church_id': user.church_id,
                    'tenant_id': request.tenant.pk,
                },
            )
            return None

        return user, validated_token


def user_may_access_tenant(user, tenant):
    """True if `user` may act inside `tenant` (None means no tenant is selected)."""
    if tenant is None:
        return True
    if user.is_superadmin:
        return True
    return user.church_id is not None and user.church_id == tenant.pk
