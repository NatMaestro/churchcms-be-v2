# 📚 Complete API Endpoints Reference

## 🔐 Authentication Endpoints

### Login/Logout

- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/logout/` - User logout
- `POST /api/v1/auth/refresh/` - Refresh JWT token

### User Management

- `GET /api/v1/auth/me/` - Get current user profile
- `GET /api/v1/auth/users/` - List all users (admin)
- `GET /api/v1/auth/users/{id}/` - Get specific user
- `POST /api/v1/auth/users/` - Create user (admin)
- `PUT /api/v1/auth/users/{id}/` - Update user
- `DELETE /api/v1/auth/users/{id}/` - Delete user

### Password Management

- `POST /api/v1/auth/change-password/` - Change password
- `POST /api/v1/auth/forgot-password/` - Request password reset
- `POST /api/v1/auth/reset-password/` - Reset password with token

---

## 👥 Member Management Endpoints

### Core Member Operations

- `GET /api/v1/members/` - List all members
- `POST /api/v1/members/` - Create new member
- `GET /api/v1/members/{id}/` - Get specific member details
- `PUT /api/v1/members/{id}/` - Update member
- `DELETE /api/v1/members/{id}/` - Delete member

### Member Sacraments

- `GET /api/v1/members/{id}/sacraments/` - Get member's sacraments
- `PUT /api/v1/members/{id}/update_sacraments/` - Update member's sacraments

### Member Import/Export

- `GET /api/v1/members/export_csv/` - Export members to CSV
- `GET /api/v1/members/export_excel/` - Export members to Excel
- `POST /api/v1/members/import_members/` - Import members from file

---

## 🏛️ Church Management Endpoints

### Church Operations

- `GET /api/v1/churches/` - List churches (admin only)
- `GET /api/v1/churches/{id}/` - Get church details
- `POST /api/v1/churches/` - Create church (admin)
- `PUT /api/v1/churches/{id}/` - Update church
- `DELETE /api/v1/churches/{id}/` - Delete church

### Church Utilities

- `GET /api/v1/churches/by-subdomain/` - Get church by subdomain
- `POST /api/v1/churches/validate-subdomain/` - Validate subdomain availability
- `GET /api/v1/churches/{id}/features/` - Get church features
- `PUT /api/v1/churches/{id}/features/` - Update church features
- `GET /api/v1/churches/{id}/church-settings/` - Get church settings
- `PUT /api/v1/churches/{id}/church-settings/` - Update church settings
- `POST /api/v1/churches/{id}/apply-denomination-defaults/` - Apply denomination defaults

---

## 📅 Event Management Endpoints

### Event Operations

- `GET /api/v1/events/` - List all events
- `POST /api/v1/events/` - Create new event
- `GET /api/v1/events/{id}/` - Get event details
- `PUT /api/v1/events/{id}/` - Update event
- `DELETE /api/v1/events/{id}/` - Delete event

### Event Registration

- `POST /api/v1/events/{id}/register/` - Register for event
- `DELETE /api/v1/events/{id}/register/` - Cancel registration
- `GET /api/v1/events/{id}/attendees/` - Get event attendees

---

## 💰 Payment Management Endpoints

### Payment Operations

- `GET /api/v1/payments/` - List all payments
- `POST /api/v1/payments/` - Record new payment
- `GET /api/v1/payments/{id}/` - Get payment details
- `PUT /api/v1/payments/{id}/` - Update payment
- `DELETE /api/v1/payments/{id}/` - Delete payment

### Payment Analytics

- `GET /api/v1/payments/stats/` - Get payment statistics
- `GET /api/v1/payments/reports/` - Generate payment reports

### Pledges

- `GET /api/v1/pledges/` - List all pledges
- `POST /api/v1/pledges/` - Create new pledge
- `GET /api/v1/pledges/{id}/` - Get pledge details
- `PUT /api/v1/pledges/{id}/` - Update pledge

### Tax Receipts

- `GET /api/v1/tax-receipts/` - List tax receipts
- `POST /api/v1/tax-receipts/` - Generate tax receipt
- `GET /api/v1/tax-receipts/{id}/` - Get receipt details

---

## 📢 Communication Endpoints

### Announcements

- `GET /api/v1/announcements/` - List announcements
- `POST /api/v1/announcements/` - Create announcement
- `GET /api/v1/announcements/{id}/` - Get announcement
- `PUT /api/v1/announcements/{id}/` - Update announcement
- `DELETE /api/v1/announcements/{id}/` - Delete announcement

### Messages

- `GET /api/v1/messages/` - List messages
- `POST /api/v1/messages/` - Send message
- `GET /api/v1/messages/{id}/` - Get message details

### Notifications

- `GET /api/v1/notifications/` - List notifications
- `POST /api/v1/notifications/{id}/mark-as-read/` - Mark notification as read
- `POST /api/v1/notifications/mark-all-read/` - Mark all notifications as read

---

## 🙏 Prayer Management Endpoints

### Prayer Requests

- `GET /api/v1/prayer-requests/` - List prayer requests
- `POST /api/v1/prayer-requests/` - Submit prayer request
- `GET /api/v1/prayer-requests/{id}/` - Get prayer request details
- `PUT /api/v1/prayer-requests/{id}/` - Update prayer request
- `DELETE /api/v1/prayer-requests/{id}/` - Delete prayer request

---

## 📊 Analytics & Reports Endpoints

### Dashboard

- `GET /api/v1/dashboard/stats/` - Get dashboard statistics
- `GET /api/v1/dashboard/member-stats/` - Get member statistics
- `GET /api/v1/dashboard/financial-stats/` - Get financial statistics

### Reports

- `GET /api/v1/reports/members/` - Generate member report
- `GET /api/v1/reports/financial/` - Generate financial report
- `GET /api/v1/reports/events/` - Generate event report

---

## 🎨 Theme Management Endpoints

### Themes

- `GET /api/v1/themes/` - List themes
- `POST /api/v1/themes/` - Create theme
- `GET /api/v1/themes/{id}/` - Get theme details
- `PUT /api/v1/themes/{id}/` - Update theme
- `DELETE /api/v1/themes/{id}/` - Delete theme

---

## 📄 Document Management Endpoints

### Documents

- `GET /api/v1/documents/` - List documents
- `POST /api/v1/documents/` - Upload document
- `GET /api/v1/documents/{id}/` - Get document details
- `PUT /api/v1/documents/{id}/` - Update document
- `DELETE /api/v1/documents/{id}/` - Delete document
- `GET /api/v1/documents/{id}/download/` - Download document

---

## 🔧 Utility Endpoints

### Debug (Development Only)

- `GET /debug/tenant/` - Debug tenant resolution

### API Documentation

- `GET /api/schema/` - OpenAPI schema
- `GET /api/docs/` - Swagger UI
- `GET /api/redoc/` - ReDoc documentation

---

## 📝 Usage Examples

### Get Current User Profile

```typescript
const response = await axiosClient.get("/auth/me/");
const user = response.data.user;
```

### List Members

```typescript
const response = await axiosClient.get("/members/");
const members = response.data.results;
```

### Get Member with Sacraments

```typescript
const memberResponse = await axiosClient.get("/members/2/");
const sacramentsResponse = await axiosClient.get("/members/2/sacraments/");
```

### Create New Member

```typescript
const newMember = await axiosClient.post("/members/", {
  member_id: "3",
  first_name: "John",
  surname: "Doe",
  email: "john@example.com",
  phone: "+1234567890",
  gender: "Male",
  date_of_birth: "1990-01-01",
  status: "active",
});
```

### Export Members

```typescript
// CSV Export
const csvResponse = await axiosClient.get("/members/export_csv/");

// Excel Export
const excelResponse = await axiosClient.get("/members/export_excel/");
```

---

## 🔒 Authentication Required

All endpoints except the following require authentication:

- `POST /auth/login/`
- `POST /auth/register/`
- `POST /auth/forgot-password/`
- `POST /auth/reset-password/`
- `GET /churches/by-subdomain/`
- `POST /churches/validate-subdomain/`

---

## 🌐 Multi-Tenancy

All endpoints automatically detect the church/tenant from the subdomain:

- `olamchurch.localhost:8000` → Olam Church data
- `deeperlife.localhost:8000` → Deeper Life data
- `testchurch.localhost:8000` → Test Church data

No need to pass `churchId` parameters!

---

**This covers all available endpoints in the FaithFlow backend!** 🚀





