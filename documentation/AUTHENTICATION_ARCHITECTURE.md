# 🔐 Authentication Architecture

## Overview

FaithFlow uses a **multi-tenant architecture** with 3 distinct user types, each with different access levels and authentication flows.

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FAITHFLOW PLATFORM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           PUBLIC SCHEMA (postgres)                       │  │
│  │                                                          │  │
│  │  • Platform Superuser                                    │  │
│  │  • Church Registry                                       │  │
│  │  • Domain Mappings                                       │  │
│  │                                                          │  │
│  │  Access: http://localhost:8000/admin/                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │        TENANT SCHEMA: olamchurch                        │  │
│  │                                                          │  │
│  │  • Church Admin (nathanielgugisberg@gmail.com)          │  │
│  │  • Church Members                                        │  │
│  │  • Church Data (events, payments, etc.)                 │  │
│  │                                                          │  │
│  │  Access: http://olamchurch.localhost:8080/              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │        TENANT SCHEMA: deeperlifeministries              │  │
│  │                                                          │  │
│  │  • Church Admin                                          │  │
│  │  • Church Members                                        │  │
│  │  • Church Data                                           │  │
│  │                                                          │  │
│  │  Access: http://deeperlifeministries.localhost:8080/    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 👥 User Types

### 1️⃣ **Platform Superuser**

**Purpose**: Manages the entire FaithFlow platform

**Schema**: `public` (shared schema)

**Capabilities**:

- View all churches and their data
- Create/edit/delete churches
- Manage platform settings
- Access Django Admin

**Login**:

```bash
# Django Admin
http://localhost:8000/admin/

# Credentials: Created via create_superuser.py
```

**Cannot**:

- Log in via tenant subdomains (e.g., olamchurch.localhost)
- Access tenant-specific frontend pages

---

### 2️⃣ **Church Admin** (Church Owner)

**Purpose**: Manages a specific church

**Schema**: Tenant schema (e.g., `olamchurch`)

**Capabilities**:

- View/manage church members
- Create/edit events, payments, announcements
- Approve member registrations
- Manage church settings
- Access church analytics

**Login**:

```bash
# Frontend Admin Dashboard
http://olamchurch.localhost:8080/admin

# API Endpoint
POST http://olamchurch.localhost:8000/api/v1/auth/login/
Body: {
  "email": "nathanielgugisberg@gmail.com",
  "password": "olam@church"
}
```

**Cannot**:

- View other churches' data
- Access platform-level settings

---

### 3️⃣ **Church Member**

**Purpose**: Regular church member

**Schema**: Same tenant schema as their church

**Capabilities**:

- View their own profile
- RSVP to events
- Make payments/donations
- Submit prayer requests
- View announcements

**Login**:

```bash
# Frontend Member Dashboard
http://olamchurch.localhost:8080/member

# API Endpoint (same as admin)
POST http://olamchurch.localhost:8000/api/v1/auth/login/
```

**Cannot**:

- View other members' data
- Manage church settings
- Access admin dashboard

---

## 🔑 Authentication Flow

### **Step 1: Subdomain Detection**

```
User accesses: http://olamchurch.localhost:8080/login
                      ↓
Frontend detects subdomain: "olamchurch"
                      ↓
API Base URL: http://olamchurch.localhost:8000/api/v1
```

### **Step 2: Tenant Resolution**

```
Request: POST http://olamchurch.localhost:8000/api/v1/auth/login/
                      ↓
Django Tenant Middleware detects subdomain: "olamchurch"
                      ↓
Looks up Church with subdomain="olamchurch"
                      ↓
Routes to tenant schema: "olamchurch"
```

### **Step 3: User Authentication**

```
JWT looks for user in "olamchurch" schema
                      ↓
Validates credentials
                      ↓
Returns JWT tokens + user data
```

---

## 🚨 Common Issues & Solutions

### ❌ **Issue: "No active account found with the given credentials"**

**Cause**: Trying to log in with credentials that don't exist in the tenant schema.

**Example**:

- You created a superuser in `public` schema
- You're trying to log in at `http://olamchurch.localhost:8000/api/v1/auth/login/`
- The superuser doesn't exist in `olamchurch` schema

**Solution**:

```bash
# Create a church admin user in the tenant schema
cd faithflow-backend
python setup_church_admin.py
```

---

### ❌ **Issue: Superuser can't access tenant data**

**Cause**: Superuser is in `public` schema, not tenant schema.

**Solution**: Superusers should:

1. Access Django Admin: `http://localhost:8000/admin/`
2. Use admin interface to view all churches
3. Create tenant-specific admin users for frontend access

---

### ❌ **Issue: Church admin can see other churches' data**

**Cause**: Tenant isolation is broken.

**Check**:

1. Is `TenantMainMiddleware` first in `MIDDLEWARE`?
2. Is user's `church_id` set correctly?
3. Are queries filtered by current tenant?

---

## 🛠️ Setup Scripts

### **Create Platform Superuser**

```bash
python create_superuser.py
# Login: http://localhost:8000/admin/
```

### **Create Church Admin**

```bash
python setup_church_admin.py
# Login: http://{subdomain}.localhost:8080/admin
```

### **Verify User in Tenant**

```bash
python verify_olam_admin.py
# Checks if user exists in olamchurch tenant
```

---

## 📊 Permission Matrix

| Action                   | Superuser | Church Admin     | Member |
| ------------------------ | --------- | ---------------- | ------ |
| View all churches        | ✅        | ❌               | ❌     |
| Manage platform settings | ✅        | ❌               | ❌     |
| View church members      | ✅        | ✅ (own church)  | ❌     |
| Create events            | ✅        | ✅               | ❌     |
| RSVP to events           | N/A       | ✅               | ✅     |
| Make payments            | N/A       | ✅               | ✅     |
| Approve members          | ✅        | ✅               | ❌     |
| Access Django Admin      | ✅        | ✅ (tenant only) | ❌     |

---

## 🔐 Security Best Practices

1. **Superuser Account**:

   - Only for platform administrators
   - Never shared with church admins
   - Separate from tenant users

2. **Church Admin**:

   - One admin per church (owner)
   - Can delegate permissions to staff
   - Cannot access other churches

3. **Members**:
   - Limited to own data
   - Cannot access admin features
   - Approved by church admin

---

## 🚀 Quick Start

### For Platform Owner:

```bash
1. python create_superuser.py
2. Access: http://localhost:8000/admin/
3. Create churches via admin interface
```

### For Church Admin:

```bash
1. python setup_church_admin.py
2. Select your church
3. Create admin credentials
4. Login: http://{subdomain}.localhost:8080/admin
```

### For Members:

- Church admin creates member accounts
- Members receive login credentials
- Login: http://{subdomain}.localhost:8080/login

---

## 📝 Notes

- **Tenant isolation** is enforced at the database level (PostgreSQL schemas)
- **JWT tokens** are tenant-specific
- **Subdomains** determine which tenant schema to use
- **Middleware** automatically handles tenant resolution




