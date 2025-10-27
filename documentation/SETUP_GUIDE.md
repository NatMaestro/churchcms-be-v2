# FaithFlow Studio Backend - Setup Guide

This comprehensive guide will help you set up and deploy the Django DRF multi-tenant backend.

## 📋 Prerequisites

- **Python**: 3.11 or higher
- **PostgreSQL**: 14 or higher (Neon PostgreSQL recommended)
- **Redis**: 7.0 or higher (for caching and Celery)
- **Node.js**: 16+ (for frontend integration testing)

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Navigate to backend directory
cd faithflow-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Configuration (Neon PostgreSQL)

#### Option A: Using Neon PostgreSQL (Recommended)

1. Create account at https://neon.tech
2. Create a new project
3. Copy connection string
4. Create `.env` file:

```env
# Copy from env.example
cp env.example .env

# Edit .env and add your Neon connection string:
DATABASE_URL=postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require

# Other required settings
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,.faithflows.com,*.faithflows.com
FRONTEND_URL=http://localhost:5173
```

#### Option B: Local PostgreSQL

```env
DB_NAME=faithflows_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### 3. Redis Setup

#### Windows (via WSL or Docker):

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or install WSL and run:
sudo apt-get install redis-server
sudo service redis-server start
```

#### macOS:

```bash
brew install redis
brew services start redis
```

#### Linux:

```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

### 4. Initialize Database

```bash
# Create migrations
python manage.py makemigrations

# Run migrations (multi-tenant aware)
python manage.py migrate_schemas

# Create public schema
python manage.py migrate_schemas --shared

# Create superuser
python manage.py createsuperuser
```

### 5. Create Initial Church (Tenant)

```python
# Run Django shell
python manage.py shell

# Create a church
from apps.churches.models import Church, Domain

# Create church
church = Church.objects.create(
    schema_name='olamchurch',  # Must be lowercase, no spaces
    name='Olam Church',
    subdomain='olamchurch',
    email='admin@olamchurch.com',
    denomination='Catholic',
    plan='trial',
    is_active=True
)

# Create domain for church
Domain.objects.create(
    domain='olamchurch.localhost',  # For local dev
    tenant=church,
    is_primary=True
)

# For production, use:
# domain='olamchurch.faithflows.com'

print(f"Church created: {church.name} (Schema: {church.schema_name})")
```

### 6. Run Development Server

```bash
# Start Django development server
python manage.py runserver

# Server will be available at:
# - Public schema: http://localhost:8000
# - Church subdomain: http://olamchurch.localhost:8000
```

### 7. Create Church Admin User

```python
# In Django shell
from apps.authentication.models import User
from apps.churches.models import Church

church = Church.objects.get(subdomain='olamchurch')

# Create admin user for church
admin_user = User.objects.create_user(
    email='admin@olamchurch.com',
    password='changeme123',
    name='Church Administrator',
    church=church,
    role='admin',
    is_active=True
)

print(f"Admin user created: {admin_user.email}")
```

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,.faithflows.com

# Database (Neon)
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# JWT
JWT_ACCESS_TOKEN_LIFETIME=60  # minutes
JWT_REFRESH_TOKEN_LIFETIME=1440  # minutes

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Email (for password reset)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Frontend
FRONTEND_URL=http://localhost:5173
```

## 📡 API Testing

### 1. Get JWT Token

```bash
# Login (Replace with your church subdomain)
curl -X POST http://olamchurch.localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@olamchurch.com",
    "password": "changeme123"
  }'

# Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "admin@olamchurch.com",
    "name": "Church Administrator",
    "role": "admin"
  }
}
```

### 2. Make Authenticated Request

```bash
# Get members (use access token from login)
curl -X GET http://olamchurch.localhost:8000/api/v1/members/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### 3. API Documentation

Access Swagger UI at:

```
http://olamchurch.localhost:8000/api/docs/
```

## 🗂️ Project Structure

```
faithflow-backend/
├── apps/
│   ├── churches/          # Church (tenant) management
│   ├── authentication/    # User authentication & JWT
│   ├── members/          # Member management
│   ├── events/           # Event management
│   ├── payments/         # Payments & giving
│   ├── ministries/       # Ministries & small groups
│   ├── volunteers/       # Volunteer opportunities
│   ├── requests/         # Service requests
│   ├── prayers/          # Prayer requests
│   ├── altarcalls/       # Altar calls
│   ├── announcements/    # Announcements
│   ├── notifications/    # Notifications
│   ├── roles/            # Roles & permissions
│   ├── themes/           # Theme customization
│   ├── documents/        # Document management
│   ├── superadmin/       # Super admin features
│   └── analytics/        # Analytics & reports
├── config/
│   ├── settings.py       # Django settings
│   ├── urls.py           # Public URLs
│   ├── urls_public.py    # Public schema URLs
│   └── urls_tenants.py   # Tenant URLs
├── core/
│   ├── middleware/       # Custom middleware
│   ├── exceptions.py     # Custom exceptions
│   └── permissions.py    # Permission classes
├── manage.py
├── requirements.txt
└── README.md
```

## 🔒 Security Checklist

- [ ] Change `SECRET_KEY` in production
- [ ] Set `DEBUG=False` in production
- [ ] Configure HTTPS/SSL
- [ ] Set up CORS properly
- [ ] Enable rate limiting
- [ ] Configure Sentry for error tracking
- [ ] Set up database backups
- [ ] Use environment variables for sensitive data
- [ ] Enable security headers
- [ ] Configure firewall rules

## 📊 Database Migrations

```bash
# Create migrations for all apps
python manage.py makemigrations

# Apply migrations to public schema
python manage.py migrate_schemas --shared

# Apply migrations to all tenants
python manage.py migrate_schemas

# Apply migrations to specific tenant
python manage.py migrate_schemas --schema=olamchurch
```

## 🎯 Next Steps

### 1. Complete Remaining Models

Create models for remaining apps:

- `apps/volunteers/models.py` - Volunteer opportunities
- `apps/requests/models.py` - Service requests
- `apps/prayers/models.py` - Prayer requests
- `apps/altarcalls/models.py` - Altar calls
- `apps/announcements/models.py` - Announcements
- `apps/roles/models.py` - Roles & permissions
- `apps/themes/models.py` - Theme settings

### 2. Create Serializers

For each model, create a serializer in `serializers.py`:

```python
# Example: apps/members/serializers.py
from rest_framework import serializers
from .models import Member

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'
```

### 3. Create ViewSets

For each model, create ViewSet in `views.py`:

```python
# Example: apps/members/views.py
from rest_framework import viewsets
from .models import Member
from .serializers import MemberSerializer

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
```

### 4. Create URL Routing

For each app, create `urls.py`:

```python
# Example: apps/members/urls.py
from rest_framework.routers import DefaultRouter
from .views import MemberViewSet

router = DefaultRouter()
router.register(r'', MemberViewSet, basename='member')

urlpatterns = router.urls
```

### 5. Test API Endpoints

```bash
# Run tests
pytest

# With coverage
pytest --cov=apps --cov-report=html
```

## 🚢 Deployment

### Deploy to Railway.app

1. Install Railway CLI:

```bash
npm install -g @railway/cli
```

2. Login and deploy:

```bash
railway login
railway init
railway up
```

3. Add environment variables in Railway dashboard

### Deploy to Render.com

1. Create `render.yaml`:

```yaml
services:
  - type: web
    name: faithflows-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn config.wsgi:application
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: SECRET_KEY
        generateValue: true
```

2. Connect GitHub repository
3. Deploy automatically

## 🆘 Troubleshooting

### Issue: Cannot connect to Neon database

**Solution**: Ensure connection string includes `?sslmode=require`

### Issue: Tenant not found

**Solution**: Check domain configuration:

```python
from apps.churches.models import Domain
Domain.objects.all()  # List all domains
```

### Issue: CORS errors

**Solution**: Add frontend URL to `CORS_ALLOWED_ORIGINS` in `.env`

### Issue: JWT token expired

**Solution**: Use refresh token to get new access token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "your-refresh-token"}'
```

## 📚 Additional Resources

- Django Documentation: https://docs.djangoproject.com/
- DRF Documentation: https://www.django-rest-framework.org/
- django-tenants Documentation: https://django-tenants.readthedocs.io/
- Neon PostgreSQL: https://neon.tech/docs

## 💬 Support

For issues and questions:

- GitHub Issues: [Create issue]
- Email: support@faithflows.com

---

**Next**: Continue building serializers, views, and complete all API endpoints!
