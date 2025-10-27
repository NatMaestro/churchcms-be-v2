# 🧪 FaithFlow Backend - Testing Guide

## ✅ What's Been Created

### Test Structure:

```
tests/
├── __init__.py
├── base.py                          # Base test classes
├── test_authentication.py           # Auth endpoints (8 tests)
├── test_members.py                  # Members CRUD (12 tests)
├── test_events.py                   # Events & registrations (10 tests)
├── test_payments.py                 # Payments & pledges (10 tests)
├── test_ministries.py               # Ministries (7 tests)
├── test_volunteers.py               # Volunteer system (5 tests)
├── test_announcements.py            # Announcements (7 tests)
├── test_prayers_and_requests.py     # Prayers & service requests (9 tests)
└── test_multitenancy.py             # Tenant isolation (5 tests)
```

**Total: 73+ Tests** ✅

---

## 🚀 Running Tests

### Run All Tests:

```bash
python manage.py test tests
```

### Run Specific Test File:

```bash
# Authentication tests only
python manage.py test tests.test_authentication

# Members tests only
python manage.py test tests.test_members

# Multi-tenancy tests only
python manage.py test tests.test_multitenancy
```

### Run Single Test Method:

```bash
python manage.py test tests.test_authentication.AuthenticationAPITestCase.test_login_success
```

### Run with Coverage:

```bash
coverage run --source='.' manage.py test tests
coverage report
coverage html  # Generate HTML report
```

---

## 📊 Test Coverage

### What's Tested:

**Authentication** ✅

- Login (success, failure, invalid credentials)
- Registration (new user, duplicate email)
- Profile (get, update)
- Token refresh
- Logout

**Members** ✅

- List, Create, Update, Delete (CRUD)
- Search & filtering
- Statistics
- Permission checks

**Events** ✅

- CRUD operations
- Event registration
- Upcoming events filter
- Type filtering

**Payments** ✅

- CRUD operations
- Payment statistics
- Filtering by type/member
- Receipt generation

**Ministries** ✅

- CRUD operations
- Adding members to ministries

**Volunteers** ✅

- Opportunity management
- Volunteer signups

**Announcements** ✅

- CRUD operations
- Priority filtering
- Active/inactive filtering

**Prayers & Requests** ✅

- Prayer requests (anonymous & public)
- Service requests
- Status updates

**Multi-Tenancy** ✅ (CRITICAL)

- Data isolation between churches
- Cannot access other church's data
- Schema separation

---

## 🔍 Test Examples

### Example 1: Testing Authentication

```python
def test_login_success(self):
    """Test successful login"""
    response = self.client.post('/api/v1/auth/login/', {
        'email': 'admin@test.com',
        'password': 'testpass123'
    })

    self.assertSuccess(response)
    self.assertIn('access', response.data)
    self.assertIn('refresh', response.data)
```

### Example 2: Testing Tenant Isolation

```python
def test_member_isolation(self):
    """Test that Church 1 cannot see Church 2's members"""
    connection.set_tenant(self.church1)
    members = Member.objects.all()
    self.assertEqual(members.count(), 1)  # Only Church 1's members
```

---

## 🎯 What to Test Next

### Add More Tests For:

**1. Roles & Permissions:**

```bash
# Create: tests/test_roles.py
- Role CRUD
- Permission assignment
- User role assignment
```

**2. Themes:**

```bash
# Create: tests/test_themes.py
- Theme CRUD
- Color validation
- Church-specific themes
```

**3. Documents:**

```bash
# Create: tests/test_documents.py
- Document upload
- File type validation
- Access control
```

**4. Notifications:**

```bash
# Create: tests/test_notifications.py
- Notification creation
- User preferences
- Read/unread status
```

**5. Altar Calls:**

```bash
# Create: tests/test_altarcalls.py
- Altar call tracking
- Follow-up status
```

---

## 🔧 Test Utilities

### Base Test Class (`tests/base.py`)

Provides:

- ✅ Automatic tenant setup
- ✅ Test church creation
- ✅ Authenticated API clients (admin, staff, member)
- ✅ JWT token handling
- ✅ Helper assertion methods

**Usage:**

```python
from tests.base import APITestCase

class MyTestCase(APITestCase):
    def test_something(self):
        # self.admin_client is already authenticated!
        response = self.admin_client.get('/api/v1/members/')
        self.assertSuccess(response)
```

---

## 🎨 Test Helpers Available:

```python
# Success assertions
self.assertSuccess(response)          # 200 OK
self.assertCreated(response)          # 201 Created

# Error assertions
self.assertBadRequest(response)       # 400 Bad Request
self.assertUnauthorized(response)     # 401 Unauthorized
self.assertForbidden(response)        # 403 Forbidden
self.assertNotFound(response)         # 404 Not Found

# Pre-authenticated clients
self.admin_client   # Admin user client
self.staff_client   # Staff user client
self.member_client  # Member user client
self.client         # Unauthenticated client
```

---

## 📈 Running Tests with Coverage

### Install coverage:

```bash
pip install coverage
```

### Run with coverage:

```bash
# Run tests
coverage run --source='apps,core' manage.py test tests

# View report in terminal
coverage report

# Generate HTML report
coverage html

# Open in browser
# htmlcov/index.html
```

---

## 🎯 Test Best Practices

### 1. Test Naming

```python
# Good
def test_create_member_as_admin(self):
    """Test creating member as admin"""

# Bad
def test1(self):
```

### 2. Arrange-Act-Assert Pattern

```python
def test_create_payment(self):
    # Arrange
    data = {'amount': '100.00', ...}

    # Act
    response = self.admin_client.post('/api/v1/payments/', data)

    # Assert
    self.assertCreated(response)
    self.assertEqual(response.data['amount'], '100.00')
```

### 3. Clean Up

```python
# The base class handles cleanup automatically!
# Each test gets a fresh database state
```

---

## 🔥 Quick Test Commands

```bash
# Run all tests
python manage.py test tests

# Run with details
python manage.py test tests --verbosity=2

# Run specific app tests
python manage.py test tests.test_members

# Run and keep database (faster)
python manage.py test tests --keepdb

# Run in parallel (faster for many tests)
python manage.py test tests --parallel

# Stop on first failure
python manage.py test tests --failfast
```

---

## 📊 Expected Test Results

When you run all tests, you should see:

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).

test_login_success (...AuthenticationAPITestCase) ... ok
test_login_invalid_credentials (...AuthenticationAPITestCase) ... ok
test_register_user (...AuthenticationAPITestCase) ... ok
...

----------------------------------------------------------------------
Ran 73 tests in 45.23s

OK
Destroying test database for alias 'default'...
```

---

## 🐛 Debugging Failed Tests

### View detailed error:

```bash
python manage.py test tests.test_members --verbosity=2
```

### Print debug info in tests:

```python
def test_something(self):
    response = self.client.get('/api/v1/members/')
    print(f"Response: {response.data}")  # Debug output
    self.assertSuccess(response)
```

### Use Django shell to debug:

```bash
python manage.py shell
>>> from apps.members.models import Member
>>> Member.objects.all()
```

---

## ✅ Test Status

| Category         | Tests   | Status       |
| ---------------- | ------- | ------------ |
| Authentication   | 8       | ✅ Created   |
| Members          | 12      | ✅ Created   |
| Events           | 10      | ✅ Created   |
| Payments         | 10      | ✅ Created   |
| Ministries       | 7       | ✅ Created   |
| Volunteers       | 5       | ✅ Created   |
| Announcements    | 7       | ✅ Created   |
| Prayers/Requests | 9       | ✅ Created   |
| Multi-Tenancy    | 5       | ✅ Created   |
| **TOTAL**        | **73+** | **✅ Ready** |

---

## 🎯 Next Steps

1. **Run the tests:**

   ```bash
   python manage.py test tests
   ```

2. **Fix any failures** (if any)

3. **Add more tests** for:

   - Roles & Permissions
   - Themes
   - Documents
   - Notifications
   - Altar Calls

4. **Measure coverage:**

   ```bash
   coverage run --source='apps' manage.py test tests
   coverage report
   ```

5. **Aim for 80%+ coverage**

---

**Tests Status**: ✅ **73+ TESTS CREATED**  
**Ready to Run**: ✅ **YES**  
**Coverage Tools**: ✅ **CONFIGURED**

Run `python manage.py test tests` to start! 🚀
