# 🌐 API Endpoint Architecture

## Overview

FaithFlow uses **role-based access control (RBAC)** where the same endpoints serve different user types with different permissions.

---

## 🔑 Authentication Endpoints

### **1. Login Endpoint**

**Endpoint**: `POST /api/v1/auth/login/`

**Access**: Public (no auth required)

**Request Body**:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response for Church Admin**:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "admin@olamchurch.com",
    "name": "Church Admin",
    "role": "admin", // ← Key difference
    "church": 5,
    "church_name": "Olam Church",
    "church_details": {
      "id": 5,
      "name": "Olam Church",
      "subdomain": "olamchurch",
      "plan": "premium"
    },
    "is_active": true,
    "is_staff": true, // ← Can access Django admin
    "must_change_password": false
  }
}
```

**Response for Member**:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 2,
    "email": "member@olamchurch.com",
    "name": "John Member",
    "role": "member", // ← Key difference
    "church": 5,
    "church_name": "Olam Church",
    "church_details": {
      "id": 5,
      "name": "Olam Church",
      "subdomain": "olamchurch",
      "plan": "premium"
    },
    "is_active": true,
    "is_staff": false, // ← Cannot access Django admin
    "must_change_password": false
  }
}
```

**Error Response** (401):

```json
{
  "success": false,
  "error": "No active account found with the given credentials",
  "status_code": 401
}
```

---

## 🛡️ Permission-Based Endpoints

### **How Permissions Work:**

The **same endpoint** returns different data based on user role:

```python
# Backend logic (simplified)
if request.user.role == 'admin':
    # Return all members
    queryset = Member.objects.all()
elif request.user.role == 'member':
    # Return only own profile
    queryset = Member.objects.filter(user=request.user)
```

---

## 📊 Endpoint Permission Matrix

### **Members Endpoint**

**Endpoint**: `GET /api/v1/members/`

| User Role           | Access              | Returns               |
| ------------------- | ------------------- | --------------------- |
| **Admin**           | ✅ Full access      | All members in church |
| **Member**          | ✅ Limited          | Own profile only      |
| **Unauthenticated** | ❌ 401 Unauthorized | Error                 |

**Admin Request**:

```bash
GET /api/v1/members/
Authorization: Bearer {admin_token}

Response: [
  { "id": 1, "name": "Admin User", "role": "admin", ... },
  { "id": 2, "name": "Member 1", "role": "member", ... },
  { "id": 3, "name": "Member 2", "role": "member", ... }
]
```

**Member Request**:

```bash
GET /api/v1/members/
Authorization: Bearer {member_token}

Response: [
  { "id": 2, "name": "Member 1", "role": "member", ... }
]
```

---

### **Events Endpoint**

**Endpoint**: `GET /api/v1/events/`

| User Role  | Can View      | Can Create | Can Edit | Can Delete |
| ---------- | ------------- | ---------- | -------- | ---------- |
| **Admin**  | ✅ All events | ✅ Yes     | ✅ All   | ✅ All     |
| **Member** | ✅ All events | ❌ No      | ❌ No    | ❌ No      |

**Create Event (Admin Only)**:

```bash
POST /api/v1/events/
Authorization: Bearer {admin_token}

Body: {
  "title": "Sunday Service",
  "date": "2025-11-01T10:00:00Z",
  "type": "service"
}

Response: 201 Created
```

**Create Event (Member)**:

```bash
POST /api/v1/events/
Authorization: Bearer {member_token}

Response: 403 Forbidden
{
  "detail": "You do not have permission to perform this action."
}
```

---

### **Payments Endpoint**

**Endpoint**: `GET /api/v1/payments/`

| User Role  | Access     | Returns                |
| ---------- | ---------- | ---------------------- |
| **Admin**  | ✅ Full    | All payments in church |
| **Member** | ✅ Limited | Only own payments      |

**Admin Request**:

```bash
GET /api/v1/payments/
Authorization: Bearer {admin_token}

Response: {
  "results": [
    { "id": 1, "member": "Member 1", "amount": 500, ... },
    { "id": 2, "member": "Member 2", "amount": 1000, ... }
  ]
}
```

**Member Request**:

```bash
GET /api/v1/payments/
Authorization: Bearer {member_token}

Response: {
  "results": [
    { "id": 2, "member": "Member 2", "amount": 1000, ... }
  ]
}
```

---

## 🔐 Middleware & Permission Checks

### **1. Tenant Middleware**

Automatically detects subdomain and routes to correct schema:

```python
# Request: http://olamchurch.localhost:8000/api/v1/members/
# Middleware: TenantMainMiddleware
#   ↓
# Detects subdomain: "olamchurch"
#   ↓
# Routes to schema: "olamchurch"
#   ↓
# All queries use "olamchurch" schema
```

### **2. Authentication Middleware**

Validates JWT token:

```python
# Header: Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
# Middleware: JWTAuthentication
#   ↓
# Validates token
#   ↓
# Sets request.user = User object
```

### **3. Permission Classes**

Check user role:

```python
class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Read permissions for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for admin
        return request.user.role == 'admin'
```

---

## 🚨 Common Issues & Solutions

### ❌ **Issue: Admin can't login but member can**

**Cause**: Admin user doesn't exist in tenant schema.

**Check**:

```bash
# Run verification script
python verify_olam_admin.py

# If user doesn't exist, create it
python setup_church_admin.py
```

---

### ❌ **Issue: Member can see all data**

**Cause**: Backend isn't filtering by user role.

**Fix**: Update viewset to filter by role:

```python
class MemberViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Member.objects.all()
        else:
            return Member.objects.filter(user=self.request.user)
```

---

### ❌ **Issue: 403 Forbidden for admin**

**Cause**: User role is not set correctly.

**Check**:

```bash
# In olamchurch schema
python manage.py shell

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from apps.churches.models import Church

User = get_user_model()
church = Church.objects.get(subdomain='olamchurch')

with schema_context(church.schema_name):
    user = User.objects.get(email='admin@olamchurch.com')
    print(f"Role: {user.role}")
    print(f"Is Staff: {user.is_staff}")

    # Fix if needed
    user.role = 'admin'
    user.is_staff = True
    user.save()
```

---

## 🎯 Frontend Route Protection

### **Based on User Role:**

```typescript
// frontend/src/routes.tsx
if (user.role === "admin") {
  // Redirect to admin dashboard
  navigate("/admin/dashboard");
} else if (user.role === "member") {
  // Redirect to member dashboard
  navigate("/member/dashboard");
}
```

### **Protected Routes:**

```typescript
<Route path="/admin/*" element={
  <RoleGuard requiredRole="admin">
    <AdminLayout />
  </RoleGuard>
} />

<Route path="/member/*" element={
  <RoleGuard requiredRole="member">
    <MemberLayout />
  </RoleGuard>
} />
```

---

## 📝 Quick Reference

### **Endpoint Pattern:**

```
Same Endpoint → Different Permissions → Different Results

GET /api/v1/members/
├── Admin Token → All members
└── Member Token → Own profile only
```

### **Permission Hierarchy:**

```
Superuser (public schema)
└── Full platform access via Django Admin

Church Admin (tenant schema)
└── Full church access via API
    ├── Create/Edit/Delete members
    ├── Create/Edit/Delete events
    └── View all church data

Member (tenant schema)
└── Limited access via API
    ├── View own profile
    ├── RSVP to events
    └── Make payments
```

---

## 🚀 Testing Endpoints

### **Test Admin Login:**

```bash
curl -X POST http://olamchurch.localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@olamchurch.com", "password": "password"}'
```

### **Test Member Login:**

```bash
curl -X POST http://olamchurch.localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "member@olamchurch.com", "password": "password"}'
```

### **Test Admin Access:**

```bash
curl -X GET http://olamchurch.localhost:8000/api/v1/members/ \
  -H "Authorization: Bearer {admin_token}"
```

### **Test Member Access:**

```bash
curl -X GET http://olamchurch.localhost:8000/api/v1/members/ \
  -H "Authorization: Bearer {member_token}"
```

---

## 🎓 Key Takeaways

1. **Same endpoint, different permissions** - Role-based access control
2. **Tenant middleware** - Automatically routes to correct schema
3. **JWT tokens** - Contain user role information
4. **Backend filtering** - Returns different data based on role
5. **Frontend routing** - Redirects based on user role

---

## 🛠️ Next Steps

1. **Create admin user**: `python setup_church_admin.py`
2. **Test login**: Use Swagger at `http://olamchurch.localhost:8000/api/docs/`
3. **Check token**: Decode JWT to verify role
4. **Test permissions**: Try accessing admin endpoints with member token




