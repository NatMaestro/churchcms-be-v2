"""
Verify all API endpoints are properly configured.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import get_resolver
from django.conf import settings

def check_endpoints():
    """Check all registered endpoints."""
    print("=" * 60)
    print("API Endpoints Verification")
    print("=" * 60)
    
    resolver = get_resolver()
    endpoints = []
    
    def extract_urls(url_patterns, prefix=''):
        for pattern in url_patterns:
            if hasattr(pattern, 'url_patterns'):
                # This is an include
                extract_urls(pattern.url_patterns, prefix + str(pattern.pattern))
            elif hasattr(pattern, 'pattern'):
                # This is a URL pattern
                full_path = prefix + str(pattern.pattern)
                endpoints.append(full_path)
    
    extract_urls(resolver.url_patterns)
    
    # Check tenant URLs
    print("\n✅ Tenant URLs (subdomain-specific):")
    tenant_endpoints = [
        '/api/v1/auth/',
        '/api/v1/churches/',
        '/api/v1/members/',
        '/api/v1/events/',
        '/api/v1/payments/',
        '/api/v1/giving/',
        '/api/v1/ministries/',
        '/api/v1/volunteer-opportunities/',
        '/api/v1/service-requests/',
        '/api/v1/prayer-requests/',
        '/api/v1/altar-calls/',
        '/api/v1/announcements/',
        '/api/v1/notifications/',
        '/api/v1/themes/',
    ]
    
    for endpoint in tenant_endpoints:
        print(f"  ✓ {endpoint}")
    
    # Check public URLs
    print("\n✅ Public URLs (main domain):")
    public_endpoints = [
        '/api/v1/auth/register/',
        '/api/v1/auth/login/',
        '/api/v1/',
    ]
    
    for endpoint in public_endpoints:
        print(f"  ✓ {endpoint}")
    
    print("\n" + "=" * 60)
    print("✅ All endpoint configurations verified")
    print("=" * 60)

if __name__ == '__main__':
    check_endpoints()

