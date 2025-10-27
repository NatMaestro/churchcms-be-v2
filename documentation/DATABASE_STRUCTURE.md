# 📊 FaithFlow Backend - Complete Database Structure

## Overview

**Total Apps**: 15 (core apps)  
**Total Models/Tables**: 28  
**Architecture**: Multi-tenant (subdomain-based isolation)

---

## 🔑 Understanding the Structure

### Django Apps vs Database Tables

- **App** = A Django module containing related functionality
- **Model** = A database table (each model creates one table)
- One app can have multiple models/tables

---

## 📋 Complete Database Schema

### 1. CHURCHES (Multi-Tenancy) - 2 Tables
*Shared Schema (Public) - Manages all church tenants*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Church** | Main tenant/church records | name, subdomain, email, denomination, plan, is_active |
| **Domain** | Subdomain mappings for each church | domain, tenant (FK), is_primary |

**Example Data**:
- Church: "Grace Community Church" → subdomain: "grace"
- Domain: "grace.localhost" → points to Grace church

---

### 2. AUTHENTICATION - 3 Tables
*Shared Schema - User authentication across all churches*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **User** | All users (admins, staff, members) | email, name, password_hash, church (FK), role |
| **UserActivity** | Audit log of user actions | user (FK), action, ip_address, timestamp |
| **PasswordResetToken** | Password reset tokens | user (FK), token, expires_at, is_used |

**User Roles**:
- SuperAdmin (platform-wide)
- Admin (church-level)
- Staff
- Member

---

### 3. MEMBERS - 3 Tables
*Tenant-specific - Isolated per church*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Member** | Member profiles | member_id, first_name, last_name, email, phone, status, sacraments (JSON) |
| **MemberWorkflow** | Workflow stages for new members | member (FK), stage, status, assigned_to (FK) |
| **MemberRequest** | Member service requests | member (FK), request_type, description, status |

**Member Statuses**:
- Active
- Inactive
- Pending
- Visitor

**Sacraments Tracked**:
- Baptism, Confirmation, First Communion, Marriage, etc.

---

### 4. EVENTS - 2 Tables
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Event** | Church events | name, type, date, location, capacity, is_recurring, recurrence_rule |
| **EventRegistration** | Event attendee registrations | event (FK), member (FK), status, registered_at |

**Event Types**:
- Sunday Service
- Bible Study
- Prayer Meeting
- Conference
- Special Event
- Youth Program
- Outreach

---

### 5. PAYMENTS - 3 Tables
*Tenant-specific - Financial transactions*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Payment** | All financial transactions | member (FK), amount, payment_type, method, date, reference |
| **Pledge** | Member pledges | member (FK), amount, frequency, start_date, end_date, status |
| **TaxReceipt** | Tax-deductible receipts | member (FK), year, total_amount, receipt_number, issued_at |

**Payment Types**:
- Tithe, Offering, Donation, Pledge, Event Fee, Membership Fee

**Payment Methods**:
- Cash, Check, Card, Bank Transfer, Mobile Money

---

### 6. MINISTRIES - 2 Tables
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Ministry** | Church ministries/departments | name, description, leader (FK), category, is_active |
| **MinistryMembership** | Members in each ministry | ministry (FK), member (FK), role, joined_at |

**Ministry Categories**:
- Worship, Youth, Children, Outreach, Media, Administration, etc.

---

### 7. VOLUNTEERS - 3 Tables
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **VolunteerOpportunity** | Available volunteer positions | title, description, ministry (FK), slots, start_date, end_date |
| **VolunteerSignup** | Member volunteer signups | opportunity (FK), member (FK), status, notes |
| **VolunteerHours** | Track volunteer hours | signup (FK), date, hours, description, verified_by (FK) |

---

### 8. REQUESTS - 1 Table
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **ServiceRequest** | General service requests | member (FK), request_type, description, priority, status, assigned_to (FK) |

**Request Types**:
- Counseling, Home Visit, Prayer, Financial Assistance, etc.

---

### 9. PRAYERS - 1 Table
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **PrayerRequest** | Prayer requests from members | member (FK), title, description, is_anonymous, status, answered_date |

**Statuses**:
- Open, Praying, Answered, Closed

---

### 10. ALTARCALLS - 1 Table
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **AltarCall** | Altar call responses | member (FK), service_date, reason, follow_up_status, assigned_to (FK), notes |

**Reasons**:
- Salvation, Rededication, Healing, Baptism, Membership

---

### 11. ANNOUNCEMENTS - 1 Table
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Announcement** | Church announcements | title, content, priority, target_audience, is_active, start_date, end_date, created_by (FK) |

**Priority Levels**:
- Low, Normal, High, Urgent

**Target Audience**:
- All Members, Leaders, Youth, Ministry-specific, etc.

---

### 12. NOTIFICATIONS - 2 Tables
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Notification** | User notifications | user (FK), title, message, notification_type, is_read, sent_at |
| **NotificationPreference** | User notification settings | user (FK), email_enabled, sms_enabled, push_enabled, frequency |

**Notification Types**:
- Event, Payment, Announcement, Prayer, Request, etc.

---

### 13. ROLES - 3 Tables
*Tenant-specific - Permission system*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Permission** | System permissions | name, codename, description, resource, action |
| **Role** | User roles | name, description, permissions (M2M), is_system_role |
| **UserRole** | Assign roles to users | user (FK), role (FK), granted_by (FK), granted_at |

**System Roles**:
- Admin, Pastor, Staff, Leader, Member

---

### 14. THEMES - 1 Table
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Theme** | Church branding/theme | primary_color, secondary_color, logo, banner, font_family, custom_css |

---

### 15. DOCUMENTS - 1 Table
*Tenant-specific*

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **Document** | Church documents/files | title, description, file_path, file_type, category, uploaded_by (FK), is_public |

**Categories**:
- Forms, Reports, Bylaws, Minutes, Resources, etc.

---

## 🗂️ Table Relationships

### Key Foreign Key Relationships

```
Church (1) ←→ (many) User
User (1) ←→ (many) Member
Member (1) ←→ (many) Payment
Member (1) ←→ (many) EventRegistration
Event (1) ←→ (many) EventRegistration
Ministry (1) ←→ (many) MinistryMembership
Member (1) ←→ (many) MinistryMembership
Member (1) ←→ (many) VolunteerSignup
VolunteerOpportunity (1) ←→ (many) VolunteerSignup
User (1) ←→ (many) Notification
User (1) ←→ (many) UserRole
Role (1) ←→ (many) UserRole
```

---

## 📊 Complete Table Count

### By Category:

**Multi-Tenancy (Shared)**:
- Churches: 2 tables

**Authentication (Shared)**:
- Authentication: 3 tables

**Core Church Management (Tenant-specific)**:
- Members: 3 tables
- Events: 2 tables
- Payments: 3 tables
- Ministries: 2 tables
- Volunteers: 3 tables

**Pastoral Care (Tenant-specific)**:
- Requests: 1 table
- Prayers: 1 table
- Altar Calls: 1 table

**Communication (Tenant-specific)**:
- Announcements: 1 table
- Notifications: 2 tables

**System (Tenant-specific)**:
- Roles: 3 tables
- Themes: 1 table
- Documents: 1 table

**Total**: **28 Tables** ✅

---

## 🔍 How to View Tables

### Option 1: Django Shell
```bash
python manage.py shell

# List all models
from django.apps import apps
for model in apps.get_models():
    print(f"{model._meta.app_label}.{model.__name__}")

# Query a specific table
from apps.members.models import Member
Member.objects.all()
```

### Option 2: Database Shell
```bash
python manage.py dbshell

# PostgreSQL commands
\dt              -- List all tables
\d+ members_member  -- Describe member table
SELECT * FROM members_member LIMIT 10;
```

### Option 3: Django Admin
```bash
python manage.py createsuperuser
# Visit: http://{subdomain}.localhost:8000/admin/
```

---

## 🎯 Are There Any Missing Tables?

### ✅ All Frontend Features Covered

Comparing to your frontend `db.json`, all data structures are implemented:

| Frontend Collection | Backend Model(s) | Status |
|-------------------|------------------|---------|
| churches | Church, Domain | ✅ |
| users | User | ✅ |
| members | Member, MemberWorkflow, MemberRequest | ✅ |
| events | Event, EventRegistration | ✅ |
| payments | Payment, Pledge, TaxReceipt | ✅ |
| ministries | Ministry, MinistryMembership | ✅ |
| volunteers | VolunteerOpportunity, VolunteerSignup, VolunteerHours | ✅ |
| requests | ServiceRequest | ✅ |
| prayers | PrayerRequest | ✅ |
| altarCalls | AltarCall | ✅ |
| announcements | Announcement | ✅ |
| notifications | Notification, NotificationPreference | ✅ |
| roles | Role, Permission, UserRole | ✅ |
| themes | Theme | ✅ |
| documents | Document | ✅ |

### 🎁 Bonus Tables (Not in Frontend)

Additional features added to the backend:

1. **UserActivity** - Audit trail for security
2. **PasswordResetToken** - Password recovery
3. **MemberWorkflow** - Onboarding process
4. **MemberRequest** - Service requests from members
5. **TaxReceipt** - Automated tax receipt generation
6. **VolunteerHours** - Track volunteer hours worked
7. **NotificationPreference** - User notification settings

---

## 📈 Database Indexes

The following indexes are automatically created for performance:

**Members**:
- `members_member_id_idx` (member_id)
- `members_email_idx` (email)
- `members_status_idx` (status)
- `members_last_name_first_name_idx` (last_name, first_name)

**Events**:
- `events_date_idx` (date)
- `events_type_idx` (type)
- `events_is_recurring_idx` (is_recurring)

**Altar Calls**:
- `altar_calls_service_date_idx` (service_date)
- `altar_calls_reason_idx` (reason)
- `altar_calls_follow_up_status_idx` (follow_up_status)

**Announcements**:
- `announcements_is_active_idx` (is_active)
- `announcements_priority_idx` (priority)
- `announcements_created_at_idx` (created_at)

---

## 💾 Data Storage

### Shared Schema (`public`)
**Contains**:
- Church records (all tenants)
- User authentication
- Domain mappings

**Location**: PostgreSQL database, `public` schema

### Tenant Schemas (per church)
**Contains**:
- All church-specific data (members, events, payments, etc.)
- Complete data isolation between churches

**Location**: PostgreSQL database, schema named after subdomain (e.g., `grace`)

**Example**:
- `grace` schema contains all data for Grace Community Church
- `hope` schema contains all data for Hope Church
- **No data sharing** between schemas

---

## 🔐 Security

### Data Isolation

Each church has a **completely isolated database schema**:

```sql
-- Grace Church data
SELECT * FROM grace.members_member;

-- Hope Church data  
SELECT * FROM hope.members_member;

-- These are COMPLETELY separate tables!
-- No way to access another church's data
```

### Multi-Tenancy Benefits

✅ Complete data isolation  
✅ Scalable to thousands of churches  
✅ Easy to backup individual churches  
✅ Easy to export/migrate church data  
✅ Per-church customization (themes, roles, etc.)  
✅ Subdomain-based access control  

---

## 🚀 Next Steps

### View Your Database:

1. **Create a church** (if you haven't):
   ```bash
   python quickstart.py
   ```

2. **Check the tables**:
   ```bash
   python manage.py dbshell
   \dt  # List all tables
   ```

3. **Use Django Admin**:
   ```bash
   python manage.py createsuperuser
   # Visit: http://{subdomain}.localhost:8000/admin/
   ```

4. **Query via API**:
   - Visit: `http://{subdomain}.localhost:8000/api/docs/`
   - Login to get JWT token
   - Try any endpoint

---

## 📝 Summary

### What You Have:

✅ **28 Database Tables** (models) across **15 Apps**  
✅ **All frontend features** migrated to backend  
✅ **7 Bonus tables** for enhanced functionality  
✅ **Multi-tenant architecture** (complete data isolation)  
✅ **Optimized indexes** for performance  
✅ **Foreign key relationships** properly set up  
✅ **Migrations applied** and database ready  

### No Missing Tables!

Every feature from your frontend is covered in the backend, plus additional enhancements for security, audit trails, and better user experience.

---

**Database Status**: ✅ **COMPLETE**  
**Total Tables**: **28**  
**Apps**: **15**  
**Ready for Use**: ✅ **YES**

---

*All tables created, indexed, and ready for your church management system!* 🎉

