from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT auth that prefers HttpOnly cookies and falls back to the Authorization header.
    This keeps browser clients on cookie-based auth to avoid localStorage token storage.
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
        return self.get_user(validated_token), validated_token

