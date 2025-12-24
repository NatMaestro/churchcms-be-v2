"""
Django settings for FaithFlow Studio Backend.
Multi-tenant church management system.
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# Load environment variables
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-development-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,.localhost,.lvh.me,.faithflows.com,*.faithflows.com').split(',')

# Tenant Settings
TENANT_MODEL = "churches.Church"
TENANT_DOMAIN_MODEL = "churches.Domain"

# Shared Apps (available to all tenants)
SHARED_APPS = [
    'django_tenants',  # Must be first
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    'sslserver',
    
    # Shared apps (multi-tenant)
    'apps.churches',
    'apps.authentication',
]

# Tenant Apps (isolated per tenant/church)
TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    
    # Tenant-specific apps
    'apps.members',
    'apps.events',
    'apps.payments',
    'apps.ministries',
    'apps.volunteers',
    'apps.requests',
    'apps.prayers',
    'apps.altarcalls',
    'apps.announcements',
    'apps.notifications',
    'apps.roles',
    'apps.themes',
    'apps.documents',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# Middleware
MIDDLEWARE = [
    # TenantHeaderMiddleware reads X-Tenant-Subdomain header and sets tenant
    # TenantMainMiddleware is kept as fallback for subdomain-based routing (optional)
    # 'django_tenants.middleware.main.TenantMainMiddleware',  # Must be first
    'core.middleware_dev.TenantHeaderMiddleware',  # Header-based tenant selection (primary) # Fallback: subdomain routing (optional)
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.middleware.csrf.DynamicCSRFMiddleware',  # Custom CSRF with dynamic subdomain support
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
    'core.middleware.TenantIsolationMiddleware',
    'core.middleware.subscription.SubscriptionMiddleware',  # Check subscription/trial status
]

ROOT_URLCONF = 'config.urls_tenants'  # Use tenant-aware URLs
PUBLIC_SCHEMA_URLCONF = 'config.urls_public'  # Public (non-tenant) URLs

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database (Multi-tenant with PostgreSQL)
# Using Neon PostgreSQL via DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL and dj_database_url:
    # Use dj_database_url to parse connection string (works with Neon, Render, etc.)
    db_config = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=0,  # Disable connection pooling to ensure tenant schema is always set correctly
        conn_health_checks=False,  # Disable to prevent connection attempts to non-existent databases
    )
    # Ensure we're using django-tenants backend
    db_config['ENGINE'] = 'django_tenants.postgresql_backend'
    DATABASES = {
        'default': db_config
    }
elif DATABASE_URL:
    # Fallback: manual parsing if dj_database_url not available
    DATABASES = {
        'default': {
            'ENGINE': 'django_tenants.postgresql_backend',
            'NAME': DATABASE_URL.split('/')[-1].split('?')[0],
            'USER': DATABASE_URL.split('://')[1].split(':')[0],
            'PASSWORD': DATABASE_URL.split(':')[2].split('@')[0],
            'HOST': DATABASE_URL.split('@')[1].split('/')[0].split(':')[0],
            'PORT': '5432',
            'OPTIONS': {
                'sslmode': 'require',
                'connect_timeout': 10,
            }
        }
    }
else:
    # Fallback for local development without DATABASE_URL
    DATABASES = {
        'default': {
            'ENGINE': 'django_tenants.postgresql_backend',
            'NAME': os.getenv('DB_NAME', 'faithflows_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# Note: Using psycopg v3 (not psycopg2)
# No code changes needed - Django 4.2+ supports both

# Authentication
AUTH_USER_MODEL = 'authentication.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Password Hashing (Argon2)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ),
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    }
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME', 60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME', 1440))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SIGNING_KEY', SECRET_KEY),
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Cookie / CSRF settings for browser-based auth
ACCESS_TOKEN_COOKIE_NAME = os.getenv('ACCESS_TOKEN_COOKIE_NAME', 'ff_access')
REFRESH_TOKEN_COOKIE_NAME = os.getenv('REFRESH_TOKEN_COOKIE_NAME', 'ff_refresh')
COOKIE_DOMAIN = os.getenv('COOKIE_DOMAIN', None)  # e.g., ".faithflow360.com" in production
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')
# CSRF_TRUSTED_ORIGINS - Base domains only (subdomains handled dynamically by DynamicCSRFMiddleware)
# The middleware automatically allows all *.faithflow360.com subdomains
CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'https://faithflow360.com,https://www.faithflow360.com'
).split(',')

# CORS Settings
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:8080,http://localhost:5173,http://localhost:3000'
).split(',')

# Allow all subdomains for local development and production
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://\w+\.localhost:\d+$",  # Match HTTPS subdomain.localhost:port
    r"^http://\w+\.localhost:\d+$",   # Match HTTP subdomain.localhost:port
    r"^https://localhost:\d+$",       # Match HTTPS localhost:port
    r"^http://localhost:\d+$",       # Match HTTP localhost:port
    r"^https://\w+\.faithflow360\.com$",  # Match subdomain.faithflow360.com (production)
    r"^https://www\.faithflow360\.com$",  # Match www.faithflow360.com (production)
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'x-tenant-subdomain',  # Custom header for multi-tenancy
    'user-agent',
    'x-csrftoken',
    'x-requested-with', 
]

# API Documentation (Spectacular)
SPECTACULAR_SETTINGS = {
    'TITLE': 'FaithFlow Studio API',
    'DESCRIPTION': 'Multi-tenant church management system API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/v1/',
}

# Email Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@faithflows.com')

# Celery Configuration (for async tasks)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Caching (Redis)
CACHES = {
    'default': {
        # Use local memory cache for development (no Redis needed)
        # Switch to Redis in production
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'faithflows-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        },
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# For production with Redis, use:
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         },
#         'KEY_PREFIX': 'faithflows',
#     }
# }

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Security Settings
# Disable SSL redirect in development to prevent 301 redirects
SECURE_SSL_REDIRECT = False  # Set to True only in production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Frontend URL
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:8080')

# Rate Limiting
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True') == 'True'
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

print(f"Database URL: {DATABASES}")
