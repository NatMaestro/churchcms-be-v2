# 🚀 Local Development Access Guide

## Multi-Tenant Access Explained

FaithFlow uses **subdomain-based multi-tenancy**. Each church has its own subdomain.

---

## 📊 Backend Access

### 1️⃣ Public Admin (Platform Management)

**URL:** `http://localhost:8000/admin/`

**What You Can Access:**

- ✅ Churches - Create/manage churches
- ✅ Domains - Subdomain mappings
- ✅ Users - All users across all churches
- ✅ User Activities - Audit logs

**What You CANNOT Access:**

- ❌ Members - Tenant-specific (access via tenant domain)
- ❌ Events - Tenant-specific
- ❌ Payments - Tenant-specific
- ❌ Prayers - Tenant-specific
- ❌ Communications - Tenant-specific

**Why?** These models exist in **tenant schemas**, not the public schema. This ensures data isolation between churches.

---

### 2️⃣ Tenant API (Church-Specific Data)

**URL:** `http://{church-subdomain}.localhost:8000/api/v1/`

**Examples:**

- `http://olamchurch.localhost:8000/api/v1/members/`
- `http://deeperlife.localhost:8000/api/v1/events/`
- `http://testchurch.localhost:8000/api/v1/payments/`

**Available Churches:**

- `olamchurch.localhost:8000`
- `deeperlife.localhost:8000`
- `testchurch.localhost:8000`

**Swagger Docs:**

- `http://olamchurch.localhost:8000/api/docs/`

---

## 🎨 Frontend Access

### ⚠️ IMPORTANT: Use Subdomain URLs!

**❌ DON'T USE:** `http://localhost:8080`
**✅ USE:** `http://olamchurch.localhost:8080`

### Why?

The frontend detects the subdomain to determine which church's data to load. Without a subdomain, it can't connect to the correct backend tenant.

### Available Frontend URLs:

- **Olam Church:** `http://olamchurch.localhost:8080`
- **Deeper Life:** `http://deeperlife.localhost:8080`
- **Test Church:** `http://testchurch.localhost:8080`

---

## 🔧 How It Works

```
┌─────────────────────────────────────────────────────┐
│  Frontend: olamchurch.localhost:8080                │
│  Detects subdomain: "olamchurch"                    │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ API Call
                   ▼
┌─────────────────────────────────────────────────────┐
│  Backend: olamchurch.localhost:8000/api/v1/         │
│  Tenant Middleware detects: "olamchurch"            │
│  Switches to olamchurch schema                      │
│  Returns olamchurch's data ONLY                     │
└─────────────────────────────────────────────────────┘
```

---

## 📝 Quick Start

### 1. Start Backend

```bash
cd faithflow-backend
python manage.py runserver
```

### 2. Start Frontend

```bash
cd faithflow-studio
npm run dev
```

### 3. Access Frontend

Open: `http://olamchurch.localhost:8080`

### 4. Login

Use the credentials you created during seeding or:

- Email: `admin@olamchurch.com`
- Password: (your password)

---

## 🐛 Troubleshooting

### Issue: "No tenant for hostname"

**Cause:** Accessing without subdomain or subdomain not in database.

**Solution:**

1. Always use subdomain URLs
2. Check domain exists: `http://localhost:8000/admin/churches/domain/`

### Issue: "CORS error"

**Cause:** Frontend and backend not using matching subdomains.

**Solution:**

- Backend CORS now allows all `*.localhost:*` patterns
- Restart backend after CORS changes

### Issue: "Can't connect to API"

**Cause:** Backend not running or wrong URL.

**Solution:**

1. Check backend is running: `http://olamchurch.localhost:8000/api/docs/`
2. Check frontend is using subdomain: `http://olamchurch.localhost:8080`

---

## 🎯 Data Access Summary

| Data Type      | Public Admin | Tenant API | Swagger UI |
| -------------- | ------------ | ---------- | ---------- |
| Churches       | ✅           | ❌         | ❌         |
| Domains        | ✅           | ❌         | ❌         |
| Users          | ✅           | ✅         | ✅         |
| Members        | ❌           | ✅         | ✅         |
| Events         | ❌           | ✅         | ✅         |
| Payments       | ❌           | ✅         | ✅         |
| Prayers        | ❌           | ✅         | ✅         |
| Communications | ❌           | ✅         | ✅         |

---

## 💡 Pro Tips

1. **Bookmark these URLs:**

   - Public Admin: `http://localhost:8000/admin/`
   - Olam Church Frontend: `http://olamchurch.localhost:8080`
   - Olam Church API Docs: `http://olamchurch.localhost:8000/api/docs/`

2. **Testing Multiple Churches:**

   - Open different church subdomains in different browser profiles
   - Each profile maintains separate auth tokens
   - Verify data isolation between churches

3. **Development Workflow:**
   - Use Public Admin for platform-level management
   - Use Swagger UI for API testing and church-specific data
   - Use Frontend for end-to-end testing

---

**Happy Coding! 🎉**
