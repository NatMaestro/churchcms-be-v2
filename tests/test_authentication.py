"""
Tests for Authentication API endpoints
"""
from django.urls import reverse
from tests.base import APITestCase
from apps.authentication.models import User


class AuthenticationAPITestCase(APITestCase):
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """Test successful login"""
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'admin@test.com',
            'password': 'testpass123'
        })
        
        self.assertSuccess(response)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'admin@test.com')
    
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'admin@test.com',
            'password': 'wrongpassword'
        })
        
        self.assertBadRequest(response)
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'fake@test.com',
            'password': 'testpass123'
        })
        
        self.assertBadRequest(response)
    
    def test_register_user(self):
        """Test user registration"""
        response = self.client.post('/api/v1/auth/register/', {
            'email': 'newuser@test.com',
            'password': 'newpass123',
            'name': 'New User',
            'role': 'member'
        })
        
        self.assertCreated(response)
        self.assertEqual(response.data['user']['email'], 'newuser@test.com')
        
        # Verify user was created
        user = User.objects.get(email='newuser@test.com')
        self.assertEqual(user.name, 'New User')
        self.assertEqual(user.role, 'member')
    
    def test_register_duplicate_email(self):
        """Test registration with existing email"""
        response = self.client.post('/api/v1/auth/register/', {
            'email': 'admin@test.com',  # Already exists
            'password': 'newpass123',
            'name': 'Duplicate User'
        })
        
        self.assertBadRequest(response)
    
    def test_get_profile_authenticated(self):
        """Test getting user profile when authenticated"""
        response = self.admin_client.get('/api/v1/auth/me/')
        
        self.assertSuccess(response)
        self.assertEqual(response.data['email'], 'admin@test.com')
        self.assertEqual(response.data['role'], 'admin')
    
    def test_get_profile_unauthenticated(self):
        """Test getting profile without authentication"""
        response = self.client.get('/api/v1/auth/me/')
        
        self.assertUnauthorized(response)
    
    def test_update_profile(self):
        """Test updating user profile"""
        response = self.admin_client.put('/api/v1/auth/me/', {
            'name': 'Updated Admin Name',
            'email': 'admin@test.com'
        })
        
        self.assertSuccess(response)
        self.assertEqual(response.data['name'], 'Updated Admin Name')
        
        # Verify in database
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.name, 'Updated Admin Name')
    
    def test_logout(self):
        """Test logout"""
        response = self.admin_client.post('/api/v1/auth/logout/')
        
        self.assertSuccess(response)
    
    def test_refresh_token(self):
        """Test refreshing access token"""
        # First login to get refresh token
        login_response = self.client.post('/api/v1/auth/login/', {
            'email': 'admin@test.com',
            'password': 'testpass123'
        })
        
        refresh_token = login_response.data['refresh']
        
        # Use refresh token to get new access token
        response = self.client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token
        })
        
        self.assertSuccess(response)
        self.assertIn('access', response.data)

