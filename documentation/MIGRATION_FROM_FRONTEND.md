Frontend to Backend Migration Guide

## 🎯 Overview

This guide explains how to migrate frontend logic to the backend API for security, performance, and proper architecture.

## 🔄 What's Been Moved to Backend

### 1. **dbUpdater.ts → Backend API** ✅

**Frontend Code (OLD - DON'T USE)**:
```typescript
// ❌ BAD: Direct database manipulation on frontend
dbUpdater.addUser(userData);
dbUpdater.addRole(roleData);
dbUpdater.updateThemeInDb(themeData);
```

**Backend API (NEW - USE THIS)**:
```typescript
// ✅ GOOD: Proper API calls
POST /api/v1/auth/users/
POST /api/v1/roles/
POST /api/v1/themes/save/
```

**Migration Steps**:
1. Replace `dbUpdater.addUser()` with API call to `/api/v1/auth/users/`
2. Replace `dbUpdater.addRole()` with API call to `/api/v1/roles/`
3. Replace `dbUpdater.updateThemeInDb()` with API call to `/api/v1/themes/save/`

### 2. **subdomainUtils.ts → Backend API** ✅

**Frontend Code (OLD)**:
```typescript
// ❌ BAD: Fetching church data directly
const church = await getChurchBySubdomain(subdomain);
const isValid = await isSubdomainValid(subdomain);
```

**Backend API (NEW)**:
```typescript
// ✅ GOOD: Backend church resolution
GET /api/v1/churches/by-subdomain/?subdomain=olamchurch
POST /api/v1/churches/validate-subdomain/
```

**Frontend Update Required**:
```typescript
// src/utils/subdomainUtils.ts - UPDATE THIS
export const getChurchBySubdomain = async (subdomain: string) => {
  const response = await axiosClient.get(`/churches/by-subdomain/?subdomain=${subdomain}`);
  return response.data.church;
};

export const isSubdomainValid = async (subdomain: string) => {
  const response = await axiosClient.post('/churches/validate-subdomain/', { subdomain });
  return response.data.available;
};
```

### 3. **denominationDefaults.ts → Backend Service** ✅

**Frontend Code (OLD)**:
```typescript
// ❌ BAD: Business logic on frontend
const defaults = getDenominationDefaults(denomination);
```

**Backend API (NEW)**:
```typescript
// ✅ GOOD: Backend handles denomination logic
GET /api/v1/churches/:id/features/  // Returns denomination-specific defaults
POST /api/v1/churches/:id/apply-denomination-defaults/
```

**What Changed**:
- Denomination defaults now calculated server-side
- Church creation automatically applies defaults
- Feature validation enforced on backend
- Can't bypass denomination restrictions

### 4. **exportUtils.ts → Backend Export Service** ✅

**Frontend Code (OLD)**:
```typescript
// ❌ BAD: Export on frontend (performance issues)
exportToCSV(data);
exportToExcel(data);
```

**Backend API (NEW)**:
```typescript
// ✅ GOOD: Server-side export
GET /api/v1/members/export-csv/
GET /api/v1/members/export-excel/
GET /api/v1/events/export-csv/
GET /api/v1/payments/export/csv/
```

**Frontend Update Required**:
```typescript
// Replace client-side export with API call
const exportMembers = async (format: 'csv' | 'excel') => {
  const endpoint = format === 'csv' 
    ? '/members/export-csv/' 
    : '/members/export-excel/';
  
  const response = await axiosClient.get(endpoint, {
    responseType: 'blob'  // Important for file download
  });
  
  // Download file
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = `members_${Date.now()}.${format}`;
  link.click();
};
```

### 5. **tokenManager.ts → Backend JWT** ✅

**What Stays on Frontend**:
- ✅ Token storage (localStorage)
- ✅ Token injection in headers
- ✅ Redirect on expiry

**What's Now Backend**:
- ✅ Token validation
- ✅ Token refresh logic
- ✅ Expiry enforcement

**Frontend Update**:
```typescript
// Keep token interceptor but use backend refresh
axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Use backend refresh endpoint
      const refreshToken = localStorage.getItem('refresh_token');
      const response = await fetch('/api/v1/auth/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken })
      });
      
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        // Retry original request
      } else {
        // Logout
        localStorage.clear();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

## 🔧 Frontend Code Changes Required

### 1. Update API Base URL

**File**: `src/api/axiosClient.ts`

```typescript
const getApiUrl = () => {
  const subdomain = window.location.hostname.split('.')[0];
  
  // Development
  if (window.location.hostname.includes('localhost')) {
    return `http://${subdomain}.localhost:8000`;
  }
  
  // Production
  return `https://${subdomain}.faithflows.com`;
};

export const axiosClient = axios.create({
  baseURL: `${getApiUrl()}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### 2. Update Authentication Service

**File**: `src/api/services/authService.ts`

```typescript
// Login
export const login = async (email: string, password: string) => {
  const response = await axiosClient.post('/auth/login/', {
    email,
    password
  });
  
  // Store tokens
  localStorage.setItem('access_token', response.data.access);
  localStorage.setItem('refresh_token', response.data.refresh);
  
  return response.data.user;
};

// Refresh token
export const refreshToken = async () => {
  const refresh = localStorage.getItem('refresh_token');
  const response = await axiosClient.post('/auth/refresh/', { refresh });
  localStorage.setItem('access_token', response.data.access);
  return response.data;
};

// Logout
export const logout = async () => {
  const refresh = localStorage.getItem('refresh_token');
  await axiosClient.post('/auth/logout/', { refresh });
  localStorage.clear();
};
```

### 3. Update Church Service

**File**: `src/api/services/churchService.ts`

```typescript
// Get church by subdomain
export const getChurchBySubdomain = async (subdomain: string) => {
  const response = await axiosClient.get(`/churches/by-subdomain/?subdomain=${subdomain}`);
  return response.data.church;
};

// Validate subdomain
export const validateSubdomain = async (subdomain: string) => {
  const response = await axiosClient.post('/churches/validate-subdomain/', { subdomain });
  return response.data;
};

// Get church features
export const getChurchFeatures = async (churchId: string) => {
  const response = await axiosClient.get(`/churches/${churchId}/features/`);
  return response.data.features;
};

// Update church features
export const updateChurchFeatures = async (churchId: string, features: any) => {
  const response = await axiosClient.put(`/churches/${churchId}/features/`, { features });
  return response.data;
};
```

### 4. Update Theme Service

**File**: `src/api/services/themeService.ts`

```typescript
// Get current theme
export const getCurrentTheme = async () => {
  const response = await axiosClient.get('/themes/current/');
  return response.data.theme;
};

// Save theme
export const saveTheme = async (themeData: any) => {
  const response = await axiosClient.post('/themes/save/', { theme: themeData });
  return response.data.theme;
};
```

### 5. Update Member Service

**File**: `src/api/services/memberService.ts`

```typescript
// Export members CSV
export const exportMembersCSV = async (filters?: any) => {
  const response = await axiosClient.get('/members/export-csv/', {
    params: filters,
    responseType: 'blob'
  });
  
  // Download file
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = `members_${Date.now()}.csv`;
  link.click();
};

// Export members Excel
export const exportMembersExcel = async (filters?: any) => {
  const response = await axiosClient.get('/members/export-excel/', {
    params: filters,
    responseType: 'blob'
  });
  
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = `members_${Date.now()}.xlsx`;
  link.click();
};
```

## 🗑️ Frontend Files to Delete/Update

### Files to DELETE (No longer needed):
- ✅ `dbUpdater.ts` - All functionality moved to backend
- ⚠️ `exportThemesToDb.ts` - Theme sync now handled by backend
- ⚠️ `themeDebugger.ts` - Use backend API for theme management

### Files to UPDATE (Keep but modify):
- ✅ `subdomainUtils.ts` - Update to call backend API
- ✅ `tokenManager.ts` - Keep client-side parts, remove server logic
- ⚠️ `denominationDefaults.ts` - Can keep for UI display only, but backend is source of truth

### Files to KEEP (No changes):
- ✅ `dateUtils.ts` - UI formatting only
- ✅ `memberUtils.ts` - UI formatting only
- ✅ `constants.ts` - Frontend constants
- ✅ `utils.ts` - General UI utilities

## 📋 Step-by-Step Migration Checklist

### Step 1: Backend Setup (DONE ✅)
- [x] All models created
- [x] Serializers created
- [x] Views created
- [x] URL routing configured
- [x] Signals for auto-notifications
- [x] Export services
- [x] Denomination service

### Step 2: Frontend API Integration (TODO)
- [ ] Update `axiosClient.ts` with correct base URL
- [ ] Update authentication service
- [ ] Update church service
- [ ] Update theme service
- [ ] Update member service
- [ ] Update all other services

### Step 3: Remove Frontend Logic (TODO)
- [ ] Delete `dbUpdater.ts`
- [ ] Update `subdomainUtils.ts` to use API
- [ ] Remove export logic from frontend
- [ ] Update theme management

### Step 4: Testing (TODO)
- [ ] Test authentication flow
- [ ] Test subdomain resolution
- [ ] Test CRUD operations
- [ ] Test exports
- [ ] Test notifications
- [ ] Test permissions

## 🚀 Quick Migration Script

Run this to quickly update frontend API calls:

```bash
# 1. Update environment variables
# Add to .env in frontend:
VITE_API_URL=http://localhost:8000

# 2. Install axios if not already
npm install axios

# 3. Update axiosClient.ts base URL
# See code above

# 4. Update all service files
# Replace direct db.json calls with API calls
```

## 🔒 Security Benefits

After migration:
- ✅ No direct database access from frontend
- ✅ All operations validated on backend
- ✅ Proper authentication & authorization
- ✅ Tenant isolation enforced
- ✅ Audit logging for all operations
- ✅ Rate limiting protection
- ✅ Input sanitization
- ✅ CORS protection

## ⚡ Performance Benefits

After migration:
- ✅ Server-side exports (no browser memory issues)
- ✅ Database query optimization
- ✅ Caching with Redis
- ✅ Pagination for large datasets
- ✅ Streaming for large files
- ✅ Background jobs for heavy operations

## 📊 Before vs After

### Before (Frontend Logic):
```
Frontend ← Direct db.json access
Frontend ← localStorage caching
Frontend ← Client-side export
Frontend ← Business logic
```

### After (Backend API):
```
Frontend → API Request → Backend → Database
Backend → Validation → Authorization → Response
Backend → Auto-notifications → Users
Backend → Export service → Streamed file
```

## 🎯 Next Steps

1. **Test backend locally**:
```bash
cd faithflow-backend
python manage.py runserver
```

2. **Update frontend API client**:
- Point to `http://localhost:8000`

3. **Test integration**:
- Login flow
- Member CRUD
- Event management
- Exports

4. **Deploy backend**:
- Choose platform (Railway, Render)
- Configure environment
- Run migrations
- Update frontend to production backend URL

## 🆘 Troubleshooting

**Issue**: CORS errors
**Solution**: Add frontend URL to `CORS_ALLOWED_ORIGINS` in backend `.env`

**Issue**: 401 Unauthorized
**Solution**: Ensure JWT token is included in request headers

**Issue**: Subdomain not resolving
**Solution**: Check domain configuration in database

**Issue**: Exports not working
**Solution**: Check `responseType: 'blob'` in axios config

---

**Status**: Backend complete ✅ | Frontend integration needed ⚠️

**Estimated Integration Time**: 4-6 hours

