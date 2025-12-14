"""
Production settings for Render deployment
"""
from .settings import *
import dj_database_url

# SECURITY
DEBUG = False
SECRET_KEY = os.getenv('SECRET_KEY')

# Hosts
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '.onrender.com,.faithflows.com,*.faithflows.com').split(',')

# Database - Use Neon PostgreSQL (DATABASE_URL from .env)
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Please set it in your .env file with your Neon PostgreSQL connection string."
    )

# Use dj_database_url to parse DATABASE_URL (works with Neon, Render, etc.)
db_config = dj_database_url.config(
    default=DATABASE_URL,
    conn_max_age=600,
    conn_health_checks=True,
)

# Ensure we're using django-tenants backend
db_config['ENGINE'] = 'django_tenants.postgresql_backend'
DATABASES['default'] = db_config

# Static Files - Use WhiteNoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CORS - Update with your frontend domain
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'https://faithflows.com,https://www.faithflows.com'
).split(',')

# Cache - Use Redis in production (if available)
redis_url = os.getenv('REDIS_URL')
if redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': redis_url,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'faithflows',
        }
    }

# Email - Configure based on your email service
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}






