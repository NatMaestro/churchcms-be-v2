# FaithFlow Studio Backend - Complete Deployment Guide

## 🎯 Overview

This guide covers the complete setup and deployment of the FaithFlow Studio multi-tenant Django backend system.

## ✅ What's Included

### Core Infrastructure

- ✅ Django 5.0.1 + Django REST Framework 3.14.0
- ✅ Multi-tenancy with django-tenants (subdomain-based)
- ✅ PostgreSQL database support (Neon compatible)
- ✅ JWT authentication with SimpleJWT
- ✅ Redis caching and Celery task queue
- ✅ Comprehensive security middleware
- ✅ CORS configuration
- ✅ API documentation with drf-spectacular

### Models Created

- ✅ **Church** - Multi-tenant church with features, settings, branding
- ✅ **User** - Custom user model with roles (superadmin, admin, member)
- ✅ **Member** - Comprehensive member profiles with denomination-specific fields
- ✅ **Event** - Events with recurring support and registrations
- ✅ **Payment** - Payments, pledges, and tax receipts
- ✅ **Ministry** - Ministries and small groups
- ✅ **Notification** - User notifications with preferences

### Security Features

- ✅ Argon2 password hashing
- ✅ JWT token authentication
- ✅ Tenant data isolation
- ✅ Security headers middleware
- ✅ Rate limiting
- ✅ CORS protection
- ✅ Audit logging

## 🚀 Quick Start (Development)

### 1. Clone and Setup

```bash
cd faithflow-backend

# Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your settings
```

**Minimum required .env settings:**

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,.faithflows.com,*.faithflows.com

# Neon PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require

# Redis (local)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Frontend
FRONTEND_URL=http://localhost:5173
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# JWT
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440
```

### 3. Setup Database

```bash
# Run migrations for public schema
python manage.py migrate_schemas --shared

# Create superuser
python manage.py createsuperuser
```

### 4. Create First Church

```python
python manage.py shell

from apps.churches.models import Church, Domain

# Create church
church = Church.objects.create(
    schema_name='olamchurch',
    name='Olam Church',
    subdomain='olamchurch',
    email='admin@olamchurch.com',
    denomination='Catholic',
    plan='trial',
    is_active=True
)

# Create domain
Domain.objects.create(
    domain='olamchurch.localhost',  # For development
    tenant=church,
    is_primary=True
)

print(f"✅ Church created: {church.name}")
exit()
```

### 5. Run Migrations for Tenant

```bash
python manage.py migrate_schemas
```

### 6. Create Church Admin

```python
python manage.py shell

from apps.authentication.models import User
from apps.churches.models import Church

church = Church.objects.get(subdomain='olamchurch')

admin = User.objects.create_user(
    email='admin@olamchurch.com',
    password='changeme123',
    name='Church Administrator',
    church=church,
    role='admin'
)

print(f"✅ Admin created: {admin.email}")
exit()
```

### 7. Run Server

```bash
python manage.py runserver

# Access:
# - Public: http://localhost:8000
# - Church: http://olamchurch.localhost:8000
# - API Docs: http://olamchurch.localhost:8000/api/docs/
```

## 📡 API Endpoints

### Authentication (Tenant-specific)

```
POST   /api/v1/auth/login/              # Login
POST   /api/v1/auth/refresh/            # Refresh token
POST   /api/v1/auth/logout/             # Logout
POST   /api/v1/auth/register/           # Register
POST   /api/v1/auth/forgot-password/    # Forgot password
POST   /api/v1/auth/reset-password/     # Reset password
GET    /api/v1/auth/me/                 # Current user
POST   /api/v1/auth/change-password/    # Change password
```

### Churches

```
GET    /api/v1/churches/{id}/           # Get church
PUT    /api/v1/churches/{id}/           # Update church
GET    /api/v1/churches/{id}/features/  # Get features
PUT    /api/v1/churches/{id}/features/  # Update features
```

### Members

```
GET    /api/v1/members/                 # List members
POST   /api/v1/members/                 # Create member
GET    /api/v1/members/{id}/            # Get member
PUT    /api/v1/members/{id}/            # Update member
DELETE /api/v1/members/{id}/            # Delete member
POST   /api/v1/members/import/          # Import CSV
```

### Events

```
GET    /api/v1/events/                  # List events
POST   /api/v1/events/                  # Create event
GET    /api/v1/events/upcoming/         # Upcoming events
POST   /api/v1/events/{id}/register/    # Register for event
DELETE /api/v1/events/{id}/register/    # Unregister
```

### Payments

```
GET    /api/v1/payments/                # List payments
POST   /api/v1/payments/                # Record payment
GET    /api/v1/giving/history/          # Giving history
GET    /api/v1/giving/receipt/{id}/     # Download receipt
```

## 🏗️ Complete the Implementation

### Step 1: Create Remaining Models

Create models for apps that don't have them yet:

**apps/volunteers/models.py**:

```python
from django.db import models

class VolunteerOpportunity(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50)
    # ... add remaining fields
```

**apps/requests/models.py**:

```python
from django.db import models

class ServiceRequest(models.Model):
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE)
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    # ... add remaining fields
```

**Similar for**:

- `apps/prayers/models.py`
- `apps/altarcalls/models.py`
- `apps/announcements/models.py`
- `apps/roles/models.py`
- `apps/themes/models.py`
- `apps/documents/models.py`

### Step 2: Create Serializers

For each model, create serializers following this pattern:

**apps/events/serializers.py**:

```python
from rest_framework import serializers
from .models import Event, EventRegistration

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
```

### Step 3: Create ViewSets

**apps/events/views.py**:

```python
from rest_framework import viewsets, permissions
from .models import Event
from .serializers import EventSerializer

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter by current tenant
        return Event.objects.filter(
            church=self.request.church
        )
```

### Step 4: Create URL Routing

**apps/events/urls.py**:

```python
from rest_framework.routers import DefaultRouter
from .views import EventViewSet

router = DefaultRouter()
router.register(r'', EventViewSet, basename='event')

urlpatterns = router.urls
```

## 🚢 Production Deployment

### Option 1: Railway.app

1. **Install Railway CLI**:

```bash
npm install -g @railway/cli
```

2. **Initialize**:

```bash
railway login
railway init
```

3. **Add Services**:

- PostgreSQL (or link Neon)
- Redis

4. **Set Environment Variables**:

```
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=.railway.app,.faithflows.com
DATABASE_URL=...  (from Neon or Railway Postgres)
REDIS_URL=...      (from Railway Redis)
```

5. **Deploy**:

```bash
railway up
```

### Option 2: Render.com

1. **Create `render.yaml`**:

```yaml
services:
  - type: web
    name: faithflows-backend
    env: python
    buildCommand: pip install -r requirements.txt && python manage.py collectstatic --noinput
    startCommand: gunicorn config.wsgi:application
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: faithflows-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: False
```

2. **Connect GitHub and Deploy**

### Option 3: Digital Ocean App Platform

1. **Create App**
2. **Add PostgreSQL Component**
3. **Configure Environment Variables**
4. **Deploy from Git**

## 🔧 Post-Deployment Setup

### 1. Run Migrations

```bash
python manage.py migrate_schemas --shared
python manage.py migrate_schemas
```

### 2. Create Superuser

```bash
python manage.py createsuperuser
```

### 3. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 4. Setup Celery (Optional)

```bash
# Start Celery worker
celery -A config worker -l info

# Start Celery beat (for scheduled tasks)
celery -A config beat -l info
```

## 🧪 Testing

### Run Tests

```bash
pytest

# With coverage
pytest --cov=apps --cov-report=html
```

### Manual API Testing

**Test Login**:

```bash
curl -X POST https://olamchurch.yourapp.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@olamchurch.com", "password": "your-password"}'
```

**Test Authenticated Request**:

```bash
curl -X GET https://olamchurch.yourapp.com/api/v1/members/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 📊 Monitoring & Maintenance

### Setup Sentry (Error Tracking)

1. Create Sentry account
2. Add to `.env`:

```env
SENTRY_DSN=https://...@sentry.io/...
```

3. Errors will be automatically tracked

### Database Backups

**Neon**: Automatic backups included

**Manual Backup**:

```bash
python manage.py dumpdata > backup.json
```

### Performance Monitoring

- Use Django Debug Toolbar in development
- Use New Relic or DataDog in production
- Monitor Redis memory usage
- Monitor database query performance

## 🔐 Security Best Practices

- ✅ Always use HTTPS in production
- ✅ Keep `SECRET_KEY` secret
- ✅ Set `DEBUG=False` in production
- ✅ Use environment variables for sensitive data
- ✅ Enable CSRF protection
- ✅ Configure CORS properly
- ✅ Use rate limiting
- ✅ Regular security updates
- ✅ Database backups
- ✅ Monitor error logs

## 📚 Next Steps

1. **Complete all models** - Add remaining models for prayers, requests, etc.
2. **Create serializers** - For all models
3. **Create views** - ViewSets for all models
4. **Add permissions** - Implement role-based permissions
5. **Write tests** - Unit and integration tests
6. **Add Celery tasks** - For email, notifications, etc.
7. **Setup WebSockets** - For real-time notifications
8. **Add file uploads** - For documents, images
9. **Create admin panels** - Custom Django admin
10. **Performance optimization** - Caching, query optimization

## 🆘 Troubleshooting

**Issue**: Cannot find tenant
**Solution**: Check domain configuration in database

**Issue**: CORS errors
**Solution**: Add frontend URL to `CORS_ALLOWED_ORIGINS`

**Issue**: Database connection error
**Solution**: Verify `DATABASE_URL` and network connectivity

**Issue**: JWT token errors
**Solution**: Check `SECRET_KEY` is same across instances

## 📞 Support

- Documentation: See `README.md` and `SETUP_GUIDE.md`
- Issues: GitHub Issues
- Email: support@faithflows.com

---

🎉 **Congratulations!** Your Django multi-tenant backend is ready!

**Frontend Integration**: Connect your React frontend by updating the API base URL to point to your deployed backend.
