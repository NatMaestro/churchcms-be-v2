"""
Tests for Multi-Tenancy Isolation
Critical tests to ensure data isolation between churches
"""
from django.test import TransactionTestCase
from django.db import connection
from rest_framework.test import APIClient

from apps.churches.models import Church, Domain
from apps.authentication.models import User
from apps.members.models import Member
from apps.events.models import Event


class MultiTenancyIsolationTestCase(TransactionTestCase):
    """
    Test that data is properly isolated between tenants
    """
    
    @classmethod
    def setUpClass(cls):
        """Create two separate churches for isolation testing"""
        super().setUpClass()
        
        # Church 1
        cls.church1, _ = Church.objects.get_or_create(
            schema_name='church1',
            defaults={
                'name': 'First Church',
                'subdomain': 'church1',
                'email': 'church1@test.com',
                'plan': 'trial',
                'is_active': True
            }
        )
        cls.domain1, _ = Domain.objects.get_or_create(
            domain='church1.localhost',
            defaults={
                'tenant': cls.church1,
                'is_primary': True
            }
        )
        
        # Church 2
        cls.church2, _ = Church.objects.get_or_create(
            schema_name='church2',
            defaults={
                'name': 'Second Church',
                'subdomain': 'church2',
                'email': 'church2@test.com',
                'plan': 'trial',
                'is_active': True
            }
        )
        cls.domain2, _ = Domain.objects.get_or_create(
            domain='church2.localhost',
            defaults={
                'tenant': cls.church2,
                'is_primary': True
            }
        )
    
    @classmethod
    def tearDownClass(cls):
        """Clean up churches"""
        connection.set_schema_to_public()
        
        if hasattr(cls, 'church1'):
            cls.church1.delete(force_drop=True)
        if hasattr(cls, 'church2'):
            cls.church2.delete(force_drop=True)
        
        super().tearDownClass()
    
    def setUp(self):
        """Set up test data for each church"""
        super().setUp()
        
        # Create data for Church 1
        connection.set_tenant(self.church1)
        
        self.user1 = User.objects.create_user(
            email='admin1@church1.com',
            password='testpass',
            name='Admin 1',
            church=self.church1,
            role='admin'
        )
        
        self.member1 = Member.objects.create(
            member_id='CH1-001',
            first_name='Church1',
            last_name='Member',
            email='member1@church1.com'
        )
        
        self.event1 = Event.objects.create(
            name='Church 1 Event',
            church=self.church1
        )
        
        # Create data for Church 2
        connection.set_tenant(self.church2)
        
        self.user2 = User.objects.create_user(
            email='admin2@church2.com',
            password='testpass',
            name='Admin 2',
            church=self.church2,
            role='admin'
        )
        
        self.member2 = Member.objects.create(
            member_id='CH2-001',
            first_name='Church2',
            last_name='Member',
            email='member2@church2.com'
        )
        
        self.event2 = Event.objects.create(
            name='Church 2 Event',
            church=self.church2
        )
    
    def test_member_isolation(self):
        """Test that Church 1 cannot see Church 2's members"""
        # Switch to Church 1
        connection.set_tenant(self.church1)
        
        # Should only see Church 1's members
        members = Member.objects.all()
        self.assertEqual(members.count(), 1)
        self.assertEqual(members.first().member_id, 'CH1-001')
        
        # Switch to Church 2
        connection.set_tenant(self.church2)
        
        # Should only see Church 2's members
        members = Member.objects.all()
        self.assertEqual(members.count(), 1)
        self.assertEqual(members.first().member_id, 'CH2-001')
    
    def test_event_isolation(self):
        """Test that churches cannot see each other's events"""
        # Church 1 events
        connection.set_tenant(self.church1)
        events = Event.objects.all()
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().name, 'Church 1 Event')
        
        # Church 2 events
        connection.set_tenant(self.church2)
        events = Event.objects.all()
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().name, 'Church 2 Event')
    
    def test_api_endpoint_isolation(self):
        """Test API endpoint isolation via subdomain"""
        # This test would require middleware setup
        # For now, we verify at the database level
        
        # Church 1 should not be able to query Church 2's data
        connection.set_tenant(self.church1)
        
        # Trying to get member from Church 2 should not work
        with self.assertRaises(Member.DoesNotExist):
            Member.objects.get(member_id='CH2-001')
        
        # Switch to Church 2
        connection.set_tenant(self.church2)
        
        # Trying to get member from Church 1 should not work
        with self.assertRaises(Member.DoesNotExist):
            Member.objects.get(member_id='CH1-001')
    
    def test_cannot_access_other_church_data_by_id(self):
        """Test that knowing an ID from another church doesn't grant access"""
        # Get Church 2 member ID
        connection.set_tenant(self.church2)
        member2_id = self.member2.id
        
        # Switch to Church 1
        connection.set_tenant(self.church1)
        
        # Try to access Church 2's member by ID - should not exist
        self.assertFalse(Member.objects.filter(id=member2_id).exists())
    
    def tearDown(self):
        """Clean up"""
        connection.set_schema_to_public()
        super().tearDown()

