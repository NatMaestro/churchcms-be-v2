"""
Security middleware for FaithFlow Studio.
Adds security headers and protections.
"""

from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        if not settings.DEBUG:
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
            
            # Content Security Policy (CSP)
            # Adjust based on your frontend domain and requirements
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.paystack.co; "  # Paystack requires unsafe-inline
                "style-src 'self' 'unsafe-inline'; "  # React/Tailwind requires unsafe-inline
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://api.paystack.co https://api.faithflow360.com; "  # API endpoints
                "frame-src https://js.paystack.co; "  # Paystack iframe
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none';"
            )
            response['Content-Security-Policy'] = csp
        
        return response






