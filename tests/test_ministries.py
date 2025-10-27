"""
Tests for Ministries API endpoints
"""
from tests.base import APITestCase
from apps.ministries.models import Ministry, MinistryMembership
from apps.members.models import Member


class MinistriesAPITestCase(APITestCase):
    """Test ministries endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test members
        self.member1 = Member.objects.create(
            member_id='MIN001',
            first_name='Leader',
            last_name='One',
            email='leader1@test.com'
        )
        
        # Create test ministries
        self.ministry1 = Ministry.objects.create(
            name='Worship Team',
            description='Sunday worship ministry',
            category='worship',
            church=self.church,
            leader=self.admin_user,
            is_active=True
        )
        
        self.ministry2 = Ministry.objects.create(
            name='Youth Ministry',
            description='Youth and young adults',
            category='youth',
            church=self.church,
            is_active=True
        )
    
    def test_list_ministries(self):
        """Test listing ministries"""
        response = self.admin_client.get('/api/v1/ministries/')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_ministry_detail(self):
        """Test getting single ministry"""
        response = self.admin_client.get(f'/api/v1/ministries/{self.ministry1.id}/')
        
        self.assertSuccess(response)
        self.assertEqual(response.data['name'], 'Worship Team')
    
    def test_create_ministry(self):
        """Test creating ministry"""
        data = {
            'name': 'Media Ministry',
            'description': 'Audio visual and streaming',
            'category': 'media',
            'leader': self.admin_user.id,
            'is_active': True
        }
        
        response = self.admin_client.post('/api/v1/ministries/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['name'], 'Media Ministry')
    
    def test_update_ministry(self):
        """Test updating ministry"""
        data = {
            'name': 'Worship Ministry - Updated',
            'description': 'Updated description',
            'category': 'worship',
            'is_active': True
        }
        
        response = self.admin_client.patch(f'/api/v1/ministries/{self.ministry1.id}/', data)
        
        self.assertSuccess(response)
        self.assertEqual(response.data['name'], 'Worship Ministry - Updated')
    
    def test_delete_ministry(self):
        """Test deleting ministry"""
        response = self.admin_client.delete(f'/api/v1/ministries/{self.ministry2.id}/')
        
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Ministry.objects.filter(id=self.ministry2.id).exists())
    
    def test_add_member_to_ministry(self):
        """Test adding member to ministry"""
        membership, created = MinistryMembership.objects.get_or_create(
            ministry=self.ministry1,
            member=self.member1,
            defaults={'role': 'member'}
        )
        
        self.assertTrue(created)
        self.assertEqual(membership.ministry.name, 'Worship Team')

