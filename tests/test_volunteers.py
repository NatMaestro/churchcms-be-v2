"""
Tests for Volunteers API endpoints
"""
from django.utils import timezone
from datetime import timedelta
from tests.base import APITestCase
from apps.volunteers.models import VolunteerOpportunity, VolunteerSignup
from apps.ministries.models import Ministry
from apps.members.models import Member


class VolunteersAPITestCase(APITestCase):
    """Test volunteers endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test ministry
        self.ministry = Ministry.objects.create(
            name='Outreach Ministry',
            church=self.church,
            is_active=True
        )
        
        # Create test member
        self.member = Member.objects.create(
            member_id='VOL001',
            first_name='Volunteer',
            last_name='Person',
            email='volunteer@test.com'
        )
        
        # Create volunteer opportunity
        self.opportunity = VolunteerOpportunity.objects.create(
            title='Sunday Greeter',
            description='Welcome people at the entrance',
            ministry=self.ministry,
            church=self.church,
            slots=5,
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=30)).date(),
            status='open'
        )
    
    def test_list_opportunities(self):
        """Test listing volunteer opportunities"""
        response = self.admin_client.get('/api/v1/volunteers/opportunities/')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_opportunity(self):
        """Test creating volunteer opportunity"""
        data = {
            'title': 'Usher',
            'description': 'Help with seating',
            'ministry': self.ministry.id,
            'slots': 10,
            'start_date': timezone.now().date().isoformat(),
            'end_date': (timezone.now() + timedelta(days=60)).date().isoformat(),
            'status': 'open'
        }
        
        response = self.admin_client.post('/api/v1/volunteers/opportunities/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['title'], 'Usher')
    
    def test_volunteer_signup(self):
        """Test signing up for volunteer opportunity"""
        data = {
            'opportunity': self.opportunity.id,
            'member': self.member.id,
            'notes': 'Available all Sundays'
        }
        
        response = self.admin_client.post('/api/v1/volunteers/signups/', data)
        
        self.assertCreated(response)
        
        # Verify signup exists
        signup = VolunteerSignup.objects.filter(
            opportunity=self.opportunity,
            member=self.member
        ).first()
        self.assertIsNotNone(signup)
    
    def test_list_signups(self):
        """Test listing volunteer signups"""
        # Create a signup first
        VolunteerSignup.objects.create(
            opportunity=self.opportunity,
            member=self.member,
            church=self.church,
            status='approved'
        )
        
        response = self.admin_client.get('/api/v1/volunteers/signups/')
        
        self.assertSuccess(response)
        self.assertGreater(len(response.data['results']), 0)






