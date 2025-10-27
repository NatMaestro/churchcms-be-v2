"""
Tests for Announcements API endpoints
"""
from django.utils import timezone
from datetime import timedelta
from tests.base import APITestCase
from apps.announcements.models import Announcement


class AnnouncementsAPITestCase(APITestCase):
    """Test announcements endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test announcements
        self.announcement1 = Announcement.objects.create(
            title='Welcome Announcement',
            content='Welcome to our church!',
            priority='normal',
            target_audience='all',
            church=self.church,
            created_by=self.admin_user,
            is_active=True,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7)
        )
        
        self.announcement2 = Announcement.objects.create(
            title='Urgent Notice',
            content='Service time changed',
            priority='urgent',
            target_audience='all',
            church=self.church,
            created_by=self.admin_user,
            is_active=True,
            start_date=timezone.now()
        )
    
    def test_list_announcements(self):
        """Test listing announcements"""
        response = self.admin_client.get('/api/v1/announcements/')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_create_announcement(self):
        """Test creating announcement"""
        data = {
            'title': 'New Announcement',
            'content': 'This is a test announcement',
            'priority': 'high',
            'target_audience': 'all',
            'is_active': True,
            'start_date': timezone.now().isoformat()
        }
        
        response = self.admin_client.post('/api/v1/announcements/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['title'], 'New Announcement')
    
    def test_filter_by_priority(self):
        """Test filtering announcements by priority"""
        response = self.admin_client.get('/api/v1/announcements/?priority=urgent')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['priority'], 'urgent')
    
    def test_filter_active_only(self):
        """Test filtering active announcements"""
        # Create inactive announcement
        Announcement.objects.create(
            title='Inactive',
            content='Old announcement',
            church=self.church,
            created_by=self.admin_user,
            is_active=False
        )
        
        response = self.admin_client.get('/api/v1/announcements/?is_active=true')
        
        self.assertSuccess(response)
        for announcement in response.data['results']:
            self.assertTrue(announcement['is_active'])
    
    def test_update_announcement(self):
        """Test updating announcement"""
        data = {
            'title': 'Updated Title',
            'content': self.announcement1.content,
            'priority': 'high',  # Changed
            'target_audience': 'all',
            'is_active': True
        }
        
        response = self.admin_client.patch(f'/api/v1/announcements/{self.announcement1.id}/', data)
        
        self.assertSuccess(response)
        self.assertEqual(response.data['priority'], 'high')
    
    def test_delete_announcement(self):
        """Test deleting announcement"""
        response = self.admin_client.delete(f'/api/v1/announcements/{self.announcement1.id}/')
        
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Announcement.objects.filter(id=self.announcement1.id).exists())

