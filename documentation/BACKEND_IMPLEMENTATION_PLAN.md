# Backend Implementation Plan - Moving Frontend Logic to Backend

## 🎯 Overview

After analyzing the frontend utils, I've identified critical functionality that **MUST** be moved to the backend for security, performance, and proper architecture.

## 🚨 Critical Issues in Current Frontend Implementation

### 1. **dbUpdater.ts** - SECURITY CRITICAL
**Problem**: Frontend is directly manipulating database records via localStorage
**Risk**: 
- No validation
- No authorization checks
- Data corruption risk
- Security vulnerability

**Must Move to Backend**:
- ✅ User creation → `POST /api/v1/auth/register/`
- ✅ Role creation → `POST /api/v1/roles/`
- ✅ Role updates → `PUT /api/v1/roles/:id/`
- ✅ User role assignment → `POST /api/v1/user-roles/assign/`
- ✅ Theme management → `POST /api/v1/themes/` & `PUT /api/v1/themes/:id/`

**Action**: Create proper API endpoints with validation

### 2. **subdomainUtils.ts** - MUST BE BACKEND
**Problem**: Church lookup happening on frontend
**Risk**:
- Exposes church data
- No server-side validation
- Cannot enforce tenant isolation

**Must Move to Backend**:
- Church lookup by subdomain
- Subdomain validation
- Church status checking (active/inactive)
- Domain resolution

**Action**: Create subdomain resolution API

### 3. **denominationDefaults.ts** - BUSINESS LOGIC
**Problem**: Business rules on frontend
**Risk**:
- Can be bypassed
- Inconsistent defaults
- No centralized control

**Must Move to Backend**:
- Denomination feature defaults
- Church feature initialization
- Feature validation rules

**Action**: Move to Church model methods

### 4. **tokenManager.ts** - SECURITY CRITICAL
**Problem**: Token validation on frontend only
**Risk**:
- Can be bypassed
- No server-side validation
- Token expiry not enforced

**Must Move to Backend**:
- Token expiry enforcement
- Token refresh logic
- Session management

**Action**: Implement in JWT middleware

### 5. **exportUtils.ts** - PERFORMANCE & SECURITY
**Problem**: Large data exports on frontend
**Risk**:
- Performance issues
- Memory problems
- No access control
- Data leakage

**Must Move to Backend**:
- CSV/Excel generation server-side
- Streamed responses for large datasets
- Proper access control
- Audit logging

**Action**: Create export API endpoints

## 📋 Implementation Checklist

### Phase 1: Critical Security Fixes (Priority 1)

#### 1.1 Church & Subdomain Resolution API
- [ ] `GET /api/v1/churches/by-subdomain/:subdomain` - Get church by subdomain
- [ ] `GET /api/v1/churches/validate-subdomain/:subdomain` - Validate subdomain
- [ ] `POST /api/v1/churches/check-availability/` - Check subdomain availability
- [ ] Middleware for automatic church resolution from subdomain

#### 1.2 Token Management
- [ ] Token refresh endpoint (already exists) ✅
- [ ] Token validation middleware ✅
- [ ] Auto-expiry enforcement
- [ ] Session management

#### 1.3 Theme Management API
- [ ] `GET /api/v1/themes/` - Get church theme
- [ ] `POST /api/v1/themes/` - Create theme
- [ ] `PUT /api/v1/themes/:id/` - Update theme
- [ ] `DELETE /api/v1/themes/:id/` - Delete theme

### Phase 2: Business Logic Migration (Priority 2)

#### 2.1 Denomination Defaults
- [ ] Move denomination logic to Church model
- [ ] `GET /api/v1/churches/:id/denomination-defaults/` - Get defaults
- [ ] Auto-apply on church creation
- [ ] Feature toggle validation

#### 2.2 Church Features Management
- [ ] `GET /api/v1/churches/:id/features/` - Get features
- [ ] `PUT /api/v1/churches/:id/features/` - Update features
- [ ] Feature validation rules
- [ ] Feature dependencies

#### 2.3 Member Utilities
- [ ] Member ID generation
- [ ] Member number sequencing
- [ ] Member validation rules
- [ ] Sacrament record validation

### Phase 3: Data Export System (Priority 2)

#### 3.1 Member Export API
- [ ] `GET /api/v1/members/export/csv/` - Export members CSV
- [ ] `GET /api/v1/members/export/xlsx/` - Export members Excel
- [ ] `POST /api/v1/members/export/custom/` - Custom field selection
- [ ] Streaming for large datasets
- [ ] Background job for massive exports

#### 3.2 Event Export API
- [ ] `GET /api/v1/events/export/csv/` - Export events CSV
- [ ] `GET /api/v1/events/export/xlsx/` - Export events Excel
- [ ] Date range filtering

#### 3.3 Financial Export API
- [ ] `GET /api/v1/payments/export/csv/` - Export payments
- [ ] `GET /api/v1/giving/export/:year/` - Annual giving export
- [ ] Tax receipt bulk generation
- [ ] Financial reports (PDF)

### Phase 4: Remaining Models & Views (Priority 3)

#### 4.1 Complete Models
- [ ] `apps/volunteers/models.py`
- [ ] `apps/requests/models.py`
- [ ] `apps/prayers/models.py`
- [ ] `apps/altarcalls/models.py`
- [ ] `apps/announcements/models.py`
- [ ] `apps/roles/models.py`
- [ ] `apps/themes/models.py`
- [ ] `apps/documents/models.py`

#### 4.2 Create Serializers & Views
- [ ] Serializers for all new models
- [ ] ViewSets with proper permissions
- [ ] URL routing
- [ ] API documentation

### Phase 5: Advanced Features (Priority 4)

#### 5.1 Auto-Notifications
- [ ] Notification triggers (signals)
- [ ] Email notifications
- [ ] SMS notifications (optional)
- [ ] In-app notifications ✅

#### 5.2 Background Tasks (Celery)
- [ ] Email sending
- [ ] Receipt generation
- [ ] Report generation
- [ ] Data cleanup

#### 5.3 WebSocket Support
- [ ] Real-time notifications
- [ ] Live updates
- [ ] Presence system

## 🏗️ New Backend Components Needed

### 1. Subdomain Middleware
```python
class SubdomainMiddleware:
    """Resolve church from subdomain automatically."""
    
    def __call__(self, request):
        subdomain = get_subdomain_from_request(request)
        if subdomain:
            request.church = Church.objects.get(subdomain=subdomain)
        return self.get_response(request)
```

### 2. Export Service
```python
class ExportService:
    """Handle all data exports with proper permissions."""
    
    def export_members_csv(self, church, filters):
        # Generate CSV server-side
        pass
    
    def export_members_xlsx(self, church, filters):
        # Generate Excel server-side
        pass
```

### 3. Church Features Service
```python
class ChurchFeaturesService:
    """Manage church features and denomination defaults."""
    
    def get_denomination_defaults(self, denomination):
        # Return feature defaults
        pass
    
    def apply_defaults(self, church):
        # Apply to church
        pass
```

### 4. Notification Service
```python
class NotificationService:
    """Create and send notifications."""
    
    def notify_members(self, church, message):
        # Send to all members
        pass
    
    def notify_admins(self, church, message):
        # Send to admins
        pass
```

## 📝 New API Endpoints Required

### Church & Subdomain
```
GET    /api/v1/churches/by-subdomain/:subdomain/
POST   /api/v1/churches/validate-subdomain/
GET    /api/v1/churches/:id/features/
PUT    /api/v1/churches/:id/features/
GET    /api/v1/churches/:id/settings/
PUT    /api/v1/churches/:id/settings/
```

### Themes
```
GET    /api/v1/themes/
GET    /api/v1/themes/:id/
POST   /api/v1/themes/
PUT    /api/v1/themes/:id/
DELETE /api/v1/themes/:id/
```

### Exports
```
GET    /api/v1/members/export/csv/
GET    /api/v1/members/export/xlsx/
POST   /api/v1/members/export/custom/
GET    /api/v1/events/export/csv/
GET    /api/v1/events/export/xlsx/
GET    /api/v1/payments/export/:year/csv/
GET    /api/v1/giving/tax-receipts/:year/generate-all/
GET    /api/v1/reports/annual-summary/:year/
```

### Denomination Features
```
GET    /api/v1/denominations/
GET    /api/v1/denominations/:id/defaults/
POST   /api/v1/churches/:id/apply-denomination-defaults/
```

## 🔐 Security Enhancements

### 1. Permission Classes
```python
class CanExportData(permissions.BasePermission):
    """Only admins can export data."""
    
class CanManageFeatures(permissions.BasePermission):
    """Only church admins can manage features."""
    
class CanGenerateReports(permissions.BasePermission):
    """Only admins can generate reports."""
```

### 2. Rate Limiting
```python
# Limit exports to prevent abuse
@ratelimit(key='user', rate='10/hour')
def export_members(request):
    pass
```

### 3. Audit Logging
```python
# Log all sensitive operations
def log_export(user, church, export_type):
    AuditLog.objects.create(
        user=user,
        church=church,
        action='export_data',
        details={'type': export_type}
    )
```

## 📊 Database Schema Updates

### 1. Add Export Tracking
```sql
CREATE TABLE export_logs (
    id UUID PRIMARY KEY,
    church_id UUID REFERENCES churches(id),
    user_id UUID REFERENCES users(id),
    export_type VARCHAR(50),
    record_count INTEGER,
    file_format VARCHAR(10),
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Add Feature Overrides
```sql
ALTER TABLE churches ADD COLUMN feature_overrides JSONB DEFAULT '{}';
ALTER TABLE churches ADD COLUMN denomination_locked BOOLEAN DEFAULT FALSE;
```

### 3. Add Session Tracking
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    token_jti VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🎯 Implementation Timeline

### Week 1: Critical Security (Phase 1)
- Days 1-2: Subdomain resolution API
- Days 3-4: Theme management API
- Day 5: Testing and deployment

### Week 2: Business Logic (Phase 2)
- Days 1-2: Denomination defaults
- Days 3-4: Church features API
- Day 5: Member utilities

### Week 3: Export System (Phase 3)
- Days 1-2: Member exports
- Day 3: Event exports
- Days 4-5: Financial exports & reports

### Week 4: Complete Models (Phase 4)
- Days 1-3: Create all remaining models
- Days 4-5: Serializers and views

### Week 5: Advanced Features (Phase 5)
- Days 1-2: Notification system
- Days 3-4: Celery tasks
- Day 5: WebSocket setup (optional)

## ✅ Success Criteria

- [ ] All database operations go through backend API
- [ ] Frontend has NO business logic
- [ ] All exports generated server-side
- [ ] Subdomain resolution on backend
- [ ] Token validation enforced server-side
- [ ] Proper permission checks on all endpoints
- [ ] Audit logging for sensitive operations
- [ ] Rate limiting on heavy operations
- [ ] Complete API test coverage

## 🚀 Quick Wins (Do First)

1. **Subdomain API** - Fixes church lookup
2. **Theme API** - Removes dbUpdater dependency
3. **Export API** - Better performance
4. **Church Features API** - Centralized control

## 📖 Documentation Updates

- [ ] Update API documentation
- [ ] Frontend integration guide
- [ ] Migration guide from client-side to server-side
- [ ] Security best practices
- [ ] Performance optimization guide

---

## 🎯 Next Immediate Steps

1. **Create Subdomain Resolution API** - CRITICAL
2. **Create Theme Management API** - HIGH
3. **Create Export Endpoints** - HIGH
4. **Complete Remaining Models** - MEDIUM
5. **Implement Notification Triggers** - MEDIUM

**Estimated Total Time**: 3-4 weeks for complete implementation

**Current Status**: Foundation complete, need to build upon it

Let's start with the critical ones! 🚀

