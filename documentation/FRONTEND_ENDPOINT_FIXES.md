# 🔧 Frontend Endpoint Fixes Required

## Issues Found:

### 1. ❌ `/api/v1/users/{id}` (Frontend calling this)

**Backend has:** `/api/v1/auth/users/{id}/`

**Frontend files to fix:**

- Any component trying to fetch user by ID should use `/auth/users/{id}/` or `/auth/me/` for current user

### 2. ❌ `/auth/profile/{userId}` (Line 240 in authService.ts)

**Backend has:** `/auth/me/` for current user OR `/auth/users/{id}/` for specific user

**Fix in:** `faithflow-studio/src/api/services/authService.ts`

```typescript
// WRONG:
async getProfile(userId: string): Promise<User> {
  const response = await axiosClient.get(`/auth/profile/${userId}`);
  return response.data;
}

// CORRECT:
async getProfile(userId?: string): Promise<User> {
  if (userId) {
    const response = await axiosClient.get(`/auth/users/${userId}/`);
    return response.data;
  } else {
    // Get current user profile
    const response = await axiosClient.get('/auth/me/');
    return response.data.user;
  }
}
```

### 3. ⚠️ Missing Trailing Slashes

Django REST Framework requires trailing slashes by default. All endpoints should have them:

**Wrong:** `/api/v1/events?churchId=5`
**Correct:** `/api/v1/events/?churchId=5`

**Wrong:** `/api/v1/announcements?churchId=5`
**Correct:** `/api/v1/announcements/?churchId=5`

### 4. ❌ `relation "events" does not exist`

The tenant schemas weren't fully migrated. Run this:

```bash
cd faithflow-backend
.\venv\Scripts\Activate.ps1
python manage.py migrate_schemas --no-input
```

---

## Backend Endpoints Reference:

### Authentication

- ✅ `POST /api/v1/auth/login/` - Login
- ✅ `POST /api/v1/auth/register/` - Register
- ✅ `POST /api/v1/auth/logout/` - Logout
- ✅ `GET /api/v1/auth/me/` - Current user profile
- ✅ `POST /api/v1/auth/refresh/` - Refresh token
- ✅ `POST /api/v1/auth/change-password/` - Change password
- ✅ `POST /api/v1/auth/forgot-password/` - Forgot password
- ✅ `POST /api/v1/auth/reset-password/` - Reset password

### Users (within auth)

- ✅ `GET /api/v1/auth/users/` - List users
- ✅ `POST /api/v1/auth/users/` - Create user
- ✅ `GET /api/v1/auth/users/{id}/` - Get user by ID
- ✅ `PUT /api/v1/auth/users/{id}/` - Update user
- ✅ `DELETE /api/v1/auth/users/{id}/` - Delete user

### Members

- ✅ `GET /api/v1/members/` - List members
- ✅ `POST /api/v1/members/` - Create member
- ✅ `GET /api/v1/members/{id}/` - Get member
- ✅ `PUT /api/v1/members/{id}/` - Update member
- ✅ `DELETE /api/v1/members/{id}/` - Delete member

### Events

- ✅ `GET /api/v1/events/` - List events
- ✅ `POST /api/v1/events/` - Create event
- ✅ `GET /api/v1/events/{id}/` - Get event
- ✅ `PUT /api/v1/events/{id}/` - Update event
- ✅ `DELETE /api/v1/events/{id}/` - Delete event

### Announcements

- ✅ `GET /api/v1/announcements/` - List announcements
- ✅ `POST /api/v1/announcements/` - Create announcement
- ✅ `GET /api/v1/announcements/{id}/` - Get announcement

### Notifications

- ✅ `GET /api/v1/notifications/` - List notifications
- ✅ `POST /api/v1/notifications/{id}/mark-as-read/` - Mark as read

---

## Quick Fixes:

### 1. Fix authService.ts getProfile method:

```bash
cd faithflow-studio/src/api/services
# Edit authService.ts line 238-244
```

Replace with:

```typescript
async getProfile(userId?: string): Promise<User> {
  try {
    if (userId) {
      const response = await axiosClient.get(`/auth/users/${userId}/`);
      return {
        id: response.data.id.toString(),
        name: response.data.name,
        email: response.data.email,
        role: response.data.role,
        churchId: response.data.church?.toString(),
        isActive: response.data.is_active,
        mustChangePassword: response.data.must_change_password || false,
        createdAt: response.data.created_at
      };
    } else {
      const response = await axiosClient.get('/auth/me/');
      return {
        id: response.data.user.id.toString(),
        name: response.data.user.name,
        email: response.data.user.email,
        role: response.data.user.role,
        churchId: response.data.user.church?.toString(),
        isActive: response.data.user.is_active,
        mustChangePassword: response.data.user.must_change_password || false,
        createdAt: response.data.user.created_at
      };
    }
  } catch (error) {
    throw new Error('Failed to fetch profile');
  }
},
```

### 2. Run migrations for tenant schemas:

```bash
cd faithflow-backend
.\venv\Scripts\Activate.ps1
python manage.py migrate_schemas --no-input
```

### 3. Ensure all API calls use trailing slashes

Check all services for endpoints without trailing slashes.

---

## Testing Checklist:

After fixes:

- [ ] Login works
- [ ] Profile page loads user data
- [ ] Members list loads
- [ ] Events list loads
- [ ] Announcements load
- [ ] No 404 errors in console
- [ ] No relation errors in backend logs





