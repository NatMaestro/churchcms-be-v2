"""
Base test class for FaithFlow API tests
Handles tenant setup and authentication
"""
from django.test import TestCase, TransactionTestCase
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.churches.models import Church, Domain
from apps.authentication.models import User


class TenantTestCase(TransactionTestCase):
    """
    Base test case for multi-tenant tests.
    Creates a test church and switches to its schema.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test church (runs once per test class)"""
        super().setUpClass()
        
        # Get or create test church (in case it already exists)
        cls.church, created = Church.objects.get_or_create(
            schema_name='test',
            defaults={
                'name': 'Test Church',
                'subdomain': 'test',
                'email': 'test@church.com',
                'plan': 'trial',
                'is_active': True
            }
        )
        
        # Get or create domain
        cls.domain, _ = Domain.objects.get_or_create(
            domain='test.localhost',
            defaults={
                'tenant': cls.church,
                'is_primary': True
            }
        )
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test church"""
        try:
            # Switch to public schema before deleting
            connection.set_schema_to_public()
            
            # Delete church (will cascade delete domain)
            if hasattr(cls, 'church'):
                cls.church.delete(force_drop=True)
        except Exception as e:
            # Ignore cleanup errors in tests
            pass
        
        super().tearDownClass()
    
    def setUp(self):
        """Set up each test - switch to tenant schema"""
        super().setUp()
        
        # Switch to tenant schema
        connection.set_tenant(self.church)
        
        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            name='Admin User',
            church=self.church,
            role='admin',
            is_active=True
        )
        
        self.staff_user = User.objects.create_user(
            email='staff@test.com',
            password='testpass123',
            name='Staff User',
            church=self.church,
            role='staff',
            is_active=True
        )
        
        self.member_user = User.objects.create_user(
            email='member@test.com',
            password='testpass123',
            name='Member User',
            church=self.church,
            role='member',
            is_active=True
        )
        
        # Set up API clients with proper tenant context
        self.client = self._create_tenant_client()
        self.admin_client = self._create_tenant_client()
        self.staff_client = self._create_tenant_client()
        self.member_client = self._create_tenant_client()
        
        # Authenticate clients
        self._authenticate_client(self.admin_client, self.admin_user)
        self._authenticate_client(self.staff_client, self.staff_user)
        self._authenticate_client(self.member_client, self.member_user)
    
    def _create_tenant_client(self):
        """Create API client with tenant context"""
        client = APIClient()
        # Set HTTP_HOST header to match tenant subdomain
        tenant_host = f'{self.church.subdomain}.localhost:8000'
        client.defaults['HTTP_HOST'] = tenant_host
        client.defaults['SERVER_NAME'] = f'{self.church.subdomain}.localhost'
        return client
    
    def _authenticate_client(self, client, user):
        """Authenticate a client with JWT token"""
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def tearDown(self):
        """Clean up after each test"""
        # Switch back to public schema
        connection.set_schema_to_public()
        super().tearDown()


class APITestCase(TenantTestCase):
    """
    Convenience class for API endpoint tests
    Includes helper methods for common operations
    """
    
    def assertSuccess(self, response, status_code=200):
        """Assert response is successful"""
        msg = f"Expected {status_code}, got {response.status_code}"
        if hasattr(response, 'data'):
            msg += f". Response: {response.data}"
        self.assertEqual(response.status_code, status_code, msg)
    
    def assertCreated(self, response):
        """Assert resource was created"""
        self.assertSuccess(response, 201)
    
    def assertBadRequest(self, response):
        """Assert bad request"""
        self.assertEqual(response.status_code, 400)
    
    def assertUnauthorized(self, response):
        """Assert unauthorized"""
        self.assertEqual(response.status_code, 401)
    
    def assertForbidden(self, response):
        """Assert forbidden"""
        self.assertEqual(response.status_code, 403)
    
    def assertNotFound(self, response):
        """Assert not found"""
        self.assertEqual(response.status_code, 404)
    
    def get_token(self, email, password):
        """Get JWT token for user"""
        response = self.client.post('/api/v1/auth/login/', {
            'email': email,
            'password': password
        })
        return response.data.get('access')

