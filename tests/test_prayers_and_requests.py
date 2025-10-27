"""
Tests for Prayer Requests and Service Requests API endpoints
"""
from tests.base import APITestCase
from apps.prayers.models import PrayerRequest
from apps.requests.models import ServiceRequest
from apps.members.models import Member


class PrayerRequestsAPITestCase(APITestCase):
    """Test prayer requests endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test member
        self.member = Member.objects.create(
            member_id='PRAY001',
            first_name='Prayer',
            last_name='Warrior',
            email='prayer@test.com'
        )
        
        # Create test prayer requests
        self.prayer1 = PrayerRequest.objects.create(
            member=self.member,
            church=self.church,
            title='Healing Prayer',
            description='Pray for healing',
            is_anonymous=False,
            status='open'
        )
    
    def test_list_prayer_requests(self):
        """Test listing prayer requests"""
        response = self.admin_client.get('/api/v1/prayers/')
        
        self.assertSuccess(response)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_create_prayer_request(self):
        """Test creating prayer request"""
        data = {
            'member': self.member.id,
            'title': 'New Prayer',
            'description': 'Please pray for my family',
            'is_anonymous': False,
            'status': 'open'
        }
        
        response = self.admin_client.post('/api/v1/prayers/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['title'], 'New Prayer')
    
    def test_update_prayer_status(self):
        """Test updating prayer request status"""
        data = {'status': 'answered'}
        
        response = self.admin_client.patch(f'/api/v1/prayers/{self.prayer1.id}/', data)
        
        self.assertSuccess(response)
        self.assertEqual(response.data['status'], 'answered')
    
    def test_anonymous_prayer_request(self):
        """Test creating anonymous prayer request"""
        data = {
            'member': self.member.id,
            'title': 'Anonymous Request',
            'description': 'Private prayer need',
            'is_anonymous': True,
            'status': 'open'
        }
        
        response = self.admin_client.post('/api/v1/prayers/', data)
        
        self.assertCreated(response)
        self.assertTrue(response.data['is_anonymous'])


class ServiceRequestsAPITestCase(APITestCase):
    """Test service requests endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test member
        self.member = Member.objects.create(
            member_id='REQ001',
            first_name='Request',
            last_name='User',
            email='request@test.com'
        )
        
        # Create test service request
        self.request1 = ServiceRequest.objects.create(
            member=self.member,
            church=self.church,
            request_type='counseling',
            description='Need counseling session',
            priority='normal',
            status='pending'
        )
    
    def test_list_service_requests(self):
        """Test listing service requests"""
        response = self.admin_client.get('/api/v1/requests/')
        
        self.assertSuccess(response)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_create_service_request(self):
        """Test creating service request"""
        data = {
            'member': self.member.id,
            'request_type': 'home_visit',
            'description': 'Please visit my home',
            'priority': 'high',
            'status': 'pending'
        }
        
        response = self.admin_client.post('/api/v1/requests/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['request_type'], 'home_visit')
    
    def test_assign_service_request(self):
        """Test assigning service request to staff"""
        data = {
            'assigned_to': self.staff_user.id,
            'status': 'assigned'
        }
        
        response = self.admin_client.patch(f'/api/v1/requests/{self.request1.id}/', data)
        
        self.assertSuccess(response)
        self.assertEqual(response.data['status'], 'assigned')
    
    def test_filter_requests_by_status(self):
        """Test filtering requests by status"""
        response = self.admin_client.get('/api/v1/requests/?status=pending')
        
        self.assertSuccess(response)
        for request in response.data['results']:
            self.assertEqual(request['status'], 'pending')
    
    def test_filter_requests_by_type(self):
        """Test filtering requests by type"""
        response = self.admin_client.get('/api/v1/requests/?request_type=counseling')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 1)

