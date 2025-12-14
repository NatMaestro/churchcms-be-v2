"""
Test-specific settings for FaithFlow Backend
"""
from .settings import *

# Override settings for testing
DEBUG = True

# Use in-memory for faster tests (optional)
# Keep regular database for multi-tenancy testing

# Disable some middleware for faster tests
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # Keep this!
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Disable custom middleware in tests for speed
    # 'core.middleware.SecurityHeadersMiddleware',
    # 'core.middleware.TenantIsolationMiddleware',
]

# Allow test hosts
ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', 'test.localhost', '.localhost']

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for faster tests (optional - can cause issues)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None

# MIGRATION_MODULES = DisableMigrations()

# Email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable throttling in tests
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '10000/hour',
    'user': '10000/hour',
}

# Test database settings
DATABASES['default']['TEST'] = {
    'NAME': 'test_neondb',
}






