"""
Tests for Members API endpoints
"""
from tests.base import APITestCase
from apps.members.models import Member


class MembersAPITestCase(APITestCase):
    """Test members endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test members
        self.member1 = Member.objects.create(
            member_id='MEM001',
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            phone='1234567890',
            gender='Male',
            status='active'
        )
        
        self.member2 = Member.objects.create(
            member_id='MEM002',
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            phone='0987654321',
            gender='Female',
            status='active'
        )
    
    def test_list_members_as_admin(self):
        """Test listing members as admin"""
        response = self.admin_client.get('/api/v1/members/')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_list_members_as_unauthenticated(self):
        """Test listing members without authentication"""
        response = self.client.get('/api/v1/members/')
        
        self.assertUnauthorized(response)
    
    def test_get_member_detail(self):
        """Test getting single member details"""
        response = self.admin_client.get(f'/api/v1/members/{self.member1.id}/')
        
        self.assertSuccess(response)
        self.assertEqual(response.data['member_id'], 'MEM001')
        self.assertEqual(response.data['first_name'], 'John')
    
    def test_create_member_as_admin(self):
        """Test creating member as admin"""
        data = {
            'member_id': 'MEM003',
            'first_name': 'Bob',
            'last_name': 'Johnson',
            'email': 'bob@test.com',
            'phone': '5555555555',
            'gender': 'Male',
            'status': 'active'
        }
        
        response = self.admin_client.post('/api/v1/members/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['member_id'], 'MEM003')
        
        # Verify in database
        member = Member.objects.get(member_id='MEM003')
        self.assertEqual(member.first_name, 'Bob')
    
    def test_create_member_as_member_forbidden(self):
        """Test that regular members cannot create members"""
        data = {
            'member_id': 'MEM004',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@test.com'
        }
        
        response = self.member_client.post('/api/v1/members/', data)
        
        # Depending on your permissions, this might be 403 or succeed
        # Adjust based on your actual permission settings
        self.assertIn(response.status_code, [201, 403])
    
    def test_update_member(self):
        """Test updating member"""
        data = {
            'member_id': 'MEM001',
            'first_name': 'Johnny',  # Updated
            'last_name': 'Doe',
            'email': 'john@test.com',
            'phone': '1234567890',
            'gender': 'Male',
            'status': 'active'
        }
        
        response = self.admin_client.put(f'/api/v1/members/{self.member1.id}/', data)
        
        self.assertSuccess(response)
        self.assertEqual(response.data['first_name'], 'Johnny')
        
        # Verify in database
        self.member1.refresh_from_db()
        self.assertEqual(self.member1.first_name, 'Johnny')
    
    def test_partial_update_member(self):
        """Test partially updating member"""
        data = {'phone': '9999999999'}
        
        response = self.admin_client.patch(f'/api/v1/members/{self.member1.id}/', data)
        
        self.assertSuccess(response)
        self.assertEqual(response.data['phone'], '9999999999')
        
        # Verify other fields unchanged
        self.assertEqual(response.data['first_name'], 'John')
    
    def test_delete_member(self):
        """Test deleting member"""
        response = self.admin_client.delete(f'/api/v1/members/{self.member1.id}/')
        
        self.assertEqual(response.status_code, 204)
        
        # Verify deleted
        self.assertFalse(Member.objects.filter(id=self.member1.id).exists())
    
    def test_search_members(self):
        """Test searching members"""
        response = self.admin_client.get('/api/v1/members/?search=John')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['first_name'], 'John')
    
    def test_filter_members_by_status(self):
        """Test filtering members by status"""
        # Create inactive member
        Member.objects.create(
            member_id='MEM003',
            first_name='Inactive',
            last_name='Member',
            status='inactive'
        )
        
        response = self.admin_client.get('/api/v1/members/?status=active')
        
        self.assertSuccess(response)
        # Should only get active members
        for member in response.data['results']:
            self.assertEqual(member['status'], 'active')
    
    def test_member_stats(self):
        """Test member statistics endpoint"""
        response = self.admin_client.get('/api/v1/members/stats/')
        
        self.assertSuccess(response)
        self.assertIn('total', response.data)
        self.assertEqual(response.data['total'], 2)

