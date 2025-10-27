# 📡 API Documentation - Swagger & ReDoc

## ✅ Swagger/OpenAPI is Fully Implemented!

Your backend includes **complete API documentation** using **drf-spectacular** (OpenAPI 3.0).

---

## 🎯 Access Swagger UI

### **Development**

**Swagger UI** (Interactive API explorer):

```
http://yourchurch.localhost:8000/api/docs/
```

**ReDoc** (Beautiful documentation):

```
http://yourchurch.localhost:8000/api/redoc/
```

**OpenAPI Schema** (JSON):

```
http://yourchurch.localhost:8000/api/schema/
```

### **Production**

Replace `localhost:8000` with your domain:

```
https://yourchurch.faithflows.com/api/docs/
https://yourchurch.faithflows.com/api/redoc/
https://yourchurch.faithflows.com/api/schema/
```

---

## 🔧 What's Configured

### **1. Package Installed**

```txt
# requirements.txt
drf-spectacular==0.27.0  # OpenAPI 3.0 schema generator
drf-yasg==1.21.7        # Alternative (Swagger 2.0)
```

### **2. Django Settings**

```python
# config/settings.py

# REST Framework configured for Swagger
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # ... other settings
}

# Swagger/OpenAPI Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'FaithFlow Studio API',
    'DESCRIPTION': 'Multi-tenant church management system API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/v1/',
}
```

### **3. URL Configuration**

```python
# config/urls_tenants.py

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # API Documentation (per tenant)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # ... your API endpoints
]
```

---

## 🎨 What You Get

### **Swagger UI Features**

✅ **Interactive API Explorer**

- Test endpoints directly in browser
- See request/response examples
- Try authentication
- View all parameters
- See response schemas

✅ **Auto-Generated Documentation**

- All 120+ endpoints documented
- Request/response schemas
- Authentication requirements
- Parameter descriptions
- Example values

✅ **Try It Out Feature**

- Execute API calls from browser
- See real responses
- Test with authentication tokens
- No need for Postman!

### **ReDoc Features**

✅ **Beautiful Documentation**

- Clean, professional interface
- Easy navigation
- Searchable
- Mobile-friendly
- Print-friendly

---

## 🔐 Testing with Swagger

### **Step 1: Access Swagger UI**

```
http://yourchurch.localhost:8000/api/docs/
```

### **Step 2: Authenticate**

1. Click "Authorize" button (top right)
2. Login first to get token:

   - Go to `POST /api/v1/auth/login/`
   - Click "Try it out"
   - Enter credentials
   - Execute
   - Copy the `access` token from response

3. Paste token in Authorization dialog:
   ```
   Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
   ```

### **Step 3: Test Endpoints**

1. Choose any endpoint
2. Click "Try it out"
3. Fill in parameters
4. Click "Execute"
5. See response!

---

## 📋 All 120+ Endpoints Documented

### **Authentication** ✅

- POST /api/v1/auth/login/
- POST /api/v1/auth/refresh/
- POST /api/v1/auth/logout/
- GET /api/v1/auth/me/
- POST /api/v1/auth/change-password/
- POST /api/v1/auth/forgot-password/
- POST /api/v1/auth/reset-password/
- POST /api/v1/auth/register/

### **Churches** ✅

- GET /api/v1/churches/
- GET /api/v1/churches/{id}/
- GET /api/v1/churches/by-subdomain/
- POST /api/v1/churches/validate-subdomain/
- GET /api/v1/churches/{id}/features/
- PUT /api/v1/churches/{id}/features/
- GET /api/v1/churches/{id}/settings/
- PUT /api/v1/churches/{id}/settings/
- And more...

### **Members** ✅

- Full CRUD operations
- Export endpoints
- Sacrament management
- Search & filtering
- And more...

### **All Other Resources** ✅

- Events (12+ endpoints)
- Payments (12+ endpoints)
- Ministries (8+ endpoints)
- Volunteers (15+ endpoints)
- Service Requests (10+ endpoints)
- Prayer Requests (8+ endpoints)
- Altar Calls (7+ endpoints)
- Announcements (8+ endpoints)
- Notifications (10+ endpoints)
- Roles (12+ endpoints)
- Documents (6+ endpoints)
- Analytics (3+ endpoints)

---

## 🎯 Swagger Features You Have

### **Automatic Features**

✅ **Request/Response Schemas** - Auto-generated from serializers
✅ **Parameter Validation** - Shows required vs optional
✅ **Authentication** - JWT token support
✅ **Try It Out** - Test endpoints in browser
✅ **Example Values** - Auto-populated
✅ **Error Responses** - Shows possible errors
✅ **Filtering** - Query parameter documentation
✅ **Pagination** - Page/limit parameters
✅ **Search** - Search functionality documented

### **Enhanced Features**

✅ **Per-Tenant Documentation** - Each church sees their API docs
✅ **Version Control** - API v1 clearly marked
✅ **OpenAPI 3.0** - Modern standard
✅ **Export Schema** - Download OpenAPI JSON
✅ **Multiple Formats** - Swagger UI + ReDoc

---

## 📖 How to Use

### **Option 1: Swagger UI** (Interactive)

```
http://yourchurch.localhost:8000/api/docs/
```

**Best for**: Testing, exploring, trying out endpoints

### **Option 2: ReDoc** (Documentation)

```
http://yourchurch.localhost:8000/api/redoc/
```

**Best for**: Reading documentation, understanding API

### **Option 3: OpenAPI Schema** (Integration)

```
http://yourchurch.localhost:8000/api/schema/
```

**Best for**: Generating client SDKs, API testing tools

---

## 🔐 Authentication in Swagger

### **Method 1: Using Authorize Button**

1. Click "Authorize" (lock icon, top right)
2. Enter: `Bearer YOUR_ACCESS_TOKEN`
3. Click "Authorize"
4. Now all requests include token!

### **Method 2: Login First**

1. Expand `POST /api/v1/auth/login/`
2. Click "Try it out"
3. Enter:
   ```json
   {
     "email": "admin@yourchurch.com",
     "password": "your-password"
   }
   ```
4. Execute
5. Copy `access` token from response
6. Use in "Authorize" button

---

## 💡 Pro Tips

### **Customize Swagger**

You can customize the Swagger settings in `config/settings.py`:

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'FaithFlow Studio API',  # Change this
    'DESCRIPTION': 'Multi-tenant church management system API',  # Change this
    'VERSION': '1.0.0',  # Update version
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/v1/',

    # Add more customization:
    'CONTACT': {
        'name': 'FaithFlow Support',
        'email': 'support@faithflows.com'
    },
    'LICENSE': {
        'name': 'MIT',
    },
}
```

### **Add Custom Documentation**

You can add descriptions to your views:

```python
class EventViewSet(viewsets.ModelViewSet):
    """
    Event management API.

    This endpoint allows you to manage church events including:
    - Creating events
    - Updating events
    - Event registration/RSVP
    - Exporting event data
    """
    queryset = Event.objects.all()
    # ...
```

### **Document Custom Actions**

```python
from drf_spectacular.utils import extend_schema

@extend_schema(
    description="Register for an event",
    request=EventRegistrationSerializer,
    responses={200: EventRegistrationSerializer}
)
@action(detail=True, methods=['post'])
def register(self, request, pk=None):
    # ...
```

---

## 🎨 Swagger UI Screenshots (What You'll See)

### **Main Page**

- List of all endpoints grouped by tags
- Authentication section at top
- Try it out buttons
- Request/response examples

### **Endpoint Details**

- HTTP method and path
- Parameters (query, path, body)
- Request body schema
- Response schemas (200, 400, 404, etc.)
- Example values
- Try it out button

### **Schemas Section**

- All your models documented
- Field types and constraints
- Required vs optional fields
- Example objects

---

## 🚀 Quick Test

Run this right now:

```bash
# 1. Start server (if not running)
python manage.py runserver

# 2. Visit Swagger UI
http://localhost:8000/api/docs/

# 3. You should see:
- FaithFlow Studio API title
- List of all endpoints
- Authorize button
- Try it out functionality
```

---

## ✅ What's Documented Automatically

**All Your Models**:

- Church, User, Member, Event, Payment, Ministry, Volunteer,
  ServiceRequest, PrayerRequest, AltarCall, Announcement,
  Notification, Role, Theme, Document

**All Your Endpoints**:

- 120+ endpoints across 16 apps
- All CRUD operations
- All custom actions
- All filters and search

**All Request/Response Formats**:

- JSON schemas for all serializers
- Example values
- Field descriptions
- Validation rules

---

## 🎊 Summary

**YES!** Swagger is fully implemented with:

✅ **drf-spectacular** (OpenAPI 3.0)  
✅ **Swagger UI** (Interactive)  
✅ **ReDoc** (Beautiful docs)  
✅ **Auto-generated** from your code  
✅ **120+ endpoints** documented  
✅ **JWT authentication** integrated  
✅ **Try it out** functionality  
✅ **Per-tenant** documentation

**Access it now**:

```
http://yourchurch.localhost:8000/api/docs/
```

**It's all ready to use! 🚀**

---

_Swagger UI is production-ready and works with all your endpoints!_
