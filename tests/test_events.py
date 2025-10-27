"""
Tests for Events API endpoints
"""
from datetime import datetime, timedelta
from django.utils import timezone
from tests.base import APITestCase
from apps.events.models import Event, EventRegistration


class EventsAPITestCase(APITestCase):
    """Test events endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test events
        self.event1 = Event.objects.create(
            name='Sunday Service',
            description='Weekly Sunday service',
            type='service',
            date=timezone.now() + timedelta(days=7),
            location='Main Hall',
            capacity=100,
            church=self.church,
            status='scheduled'
        )
        
        self.event2 = Event.objects.create(
            name='Bible Study',
            description='Wednesday Bible study',
            type='bible_study',
            date=timezone.now() + timedelta(days=3),
            location='Fellowship Hall',
            capacity=50,
            church=self.church,
            status='scheduled'
        )
    
    def test_list_events(self):
        """Test listing events"""
        response = self.admin_client.get('/api/v1/events/')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_event_detail(self):
        """Test getting single event"""
        response = self.admin_client.get(f'/api/v1/events/{self.event1.id}/')
        
        self.assertSuccess(response)
        self.assertEqual(response.data['name'], 'Sunday Service')
    
    def test_create_event(self):
        """Test creating event"""
        data = {
            'name': 'Youth Conference',
            'description': 'Annual youth conference',
            'type': 'conference',
            'date': (timezone.now() + timedelta(days=30)).isoformat(),
            'location': 'Conference Center',
            'capacity': 200,
            'status': 'scheduled'
        }
        
        response = self.admin_client.post('/api/v1/events/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['name'], 'Youth Conference')
        
        # Verify in database
        event = Event.objects.get(name='Youth Conference')
        self.assertEqual(event.type, 'conference')
    
    def test_update_event(self):
        """Test updating event"""
        data = {
            'name': 'Sunday Service - Updated',
            'description': self.event1.description,
            'type': self.event1.type,
            'date': self.event1.date.isoformat(),
            'location': self.event1.location,
            'capacity': 150,  # Updated
            'status': self.event1.status
        }
        
        response = self.admin_client.put(f'/api/v1/events/{self.event1.id}/', data)
        
        self.assertSuccess(response)
        self.assertEqual(response.data['capacity'], 150)
    
    def test_delete_event(self):
        """Test deleting event"""
        response = self.admin_client.delete(f'/api/v1/events/{self.event1.id}/')
        
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Event.objects.filter(id=self.event1.id).exists())
    
    def test_get_upcoming_events(self):
        """Test getting upcoming events"""
        response = self.admin_client.get('/api/v1/events/upcoming/')
        
        self.assertSuccess(response)
        # Both events are in the future
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_register_for_event(self):
        """Test event registration"""
        response = self.admin_client.post(f'/api/v1/events/{self.event1.id}/register/')
        
        self.assertCreated(response)
        
        # Verify registration exists
        registration = EventRegistration.objects.filter(
            event=self.event1,
            user=self.admin_user
        ).first()
        self.assertIsNotNone(registration)
    
    def test_filter_events_by_type(self):
        """Test filtering events by type"""
        response = self.admin_client.get('/api/v1/events/?type=service')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['type'], 'service')

