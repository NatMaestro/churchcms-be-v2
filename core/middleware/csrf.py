"""
Custom CSRF middleware that dynamically allows subdomains of faithflow360.com.
This extends Django's CSRF middleware to support wildcard subdomain validation.
"""
import re
from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.deprecation import MiddlewareMixin


class DynamicCSRFMiddleware(CsrfViewMiddleware, MiddlewareMixin):
    """
    CSRF middleware that dynamically validates origins for subdomains.
    
    Allows:
    - Origins explicitly listed in CSRF_TRUSTED_ORIGINS
    - Any subdomain of faithflow360.com (e.g., apostolicchurchghana.faithflow360.com)
    - Localhost origins for development
    """
    
    # Patterns for allowed subdomains
    ALLOWED_SUBDOMAIN_PATTERNS = [
        r'^https://[\w-]+\.faithflow360\.com$',  # Production subdomains
        r'^https://www\.faithflow360\.com$',     # www subdomain
        r'^https://[\w-]+\.localhost:\d+$',      # Local HTTPS dev subdomains
        r'^http://[\w-]+\.localhost:\d+$',       # Local HTTP dev subdomains
        r'^https://localhost:\d+$',               # Local HTTPS dev
        r'^http://localhost:\d+$',               # Local HTTP dev
    ]
    
    def _origin_trusted(self, origin):
        """
        Check if origin is trusted, including dynamic subdomain validation.
        """
        if not origin:
            return False
        
        # Check explicit trusted origins first
        if origin in settings.CSRF_TRUSTED_ORIGINS:
            return True
        
        # Check against subdomain patterns
        for pattern in self.ALLOWED_SUBDOMAIN_PATTERNS:
            if re.match(pattern, origin):
                return True
        
        return False
    
    def _check_origin(self, request):
        """
        Override origin check to include dynamic subdomain validation.
        """
        origin = request.META.get('HTTP_ORIGIN')
        referer = request.META.get('HTTP_REFERER')
        
        # If no origin, try to extract from referer
        if not origin and referer:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass
        
        # Check our dynamic patterns first
        if origin and self._origin_trusted(origin):
            return True
        
        # Fall back to parent class validation (checks CSRF_TRUSTED_ORIGINS)
        return super()._check_origin(request)
    
    def process_request(self, request):
        """
        Process the request and validate CSRF token.
        """
        # Call parent to handle standard CSRF validation
        return super().process_request(request)

