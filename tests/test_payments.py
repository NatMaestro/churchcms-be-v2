"""
Tests for Payments API endpoints
"""
from decimal import Decimal
from django.utils import timezone
from tests.base import APITestCase
from apps.payments.models import Payment, Pledge
from apps.members.models import Member


class PaymentsAPITestCase(APITestCase):
    """Test payments endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test member
        self.member = Member.objects.create(
            member_id='PAY001',
            first_name='John',
            last_name='Donor',
            email='donor@test.com'
        )
        
        # Create test payments
        self.payment1 = Payment.objects.create(
            member=self.member,
            church=self.church,
            amount=Decimal('100.00'),
            payment_type='tithe',
            method='cash',
            date=timezone.now(),
            reference='REF001'
        )
        
        self.payment2 = Payment.objects.create(
            member=self.member,
            church=self.church,
            amount=Decimal('50.00'),
            payment_type='offering',
            method='card',
            date=timezone.now(),
            reference='REF002'
        )
    
    def test_list_payments(self):
        """Test listing payments"""
        response = self.admin_client.get('/api/v1/payments/')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_payment_detail(self):
        """Test getting single payment"""
        response = self.admin_client.get(f'/api/v1/payments/{self.payment1.id}/')
        
        self.assertSuccess(response)
        self.assertEqual(response.data['reference'], 'REF001')
        self.assertEqual(float(response.data['amount']), 100.00)
    
    def test_create_payment(self):
        """Test creating payment"""
        data = {
            'member': self.member.id,
            'amount': '75.50',
            'payment_type': 'donation',
            'method': 'bank_transfer',
            'date': timezone.now().isoformat(),
            'reference': 'REF003',
            'notes': 'Test donation'
        }
        
        response = self.admin_client.post('/api/v1/payments/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['reference'], 'REF003')
        
        # Verify in database
        payment = Payment.objects.get(reference='REF003')
        self.assertEqual(payment.amount, Decimal('75.50'))
    
    def test_get_payment_stats(self):
        """Test payment statistics"""
        response = self.admin_client.get('/api/v1/payments/stats/')
        
        self.assertSuccess(response)
        self.assertIn('total_amount', response.data)
        # Total should be 100 + 50 = 150
        self.assertEqual(float(response.data['total_amount']), 150.00)
    
    def test_filter_payments_by_type(self):
        """Test filtering payments by type"""
        response = self.admin_client.get('/api/v1/payments/?payment_type=tithe')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['payment_type'], 'tithe')
    
    def test_filter_payments_by_member(self):
        """Test filtering payments by member"""
        response = self.admin_client.get(f'/api/v1/payments/?member={self.member.id}')
        
        self.assertSuccess(response)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_payment_receipt(self):
        """Test generating payment receipt"""
        response = self.admin_client.get(f'/api/v1/payments/{self.payment1.id}/receipt/')
        
        self.assertSuccess(response)
        self.assertIn('receipt', response.data)


class PledgesAPITestCase(APITestCase):
    """Test pledges endpoints"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test member
        self.member = Member.objects.create(
            member_id='PLG001',
            first_name='Jane',
            last_name='Pledger',
            email='pledger@test.com'
        )
        
        # Create test pledge
        self.pledge = Pledge.objects.create(
            member=self.member,
            church=self.church,
            amount=Decimal('1000.00'),
            frequency='monthly',
            start_date=timezone.now().date(),
            status='active'
        )
    
    def test_list_pledges(self):
        """Test listing pledges"""
        response = self.admin_client.get('/api/v1/pledges/')
        
        self.assertSuccess(response)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_create_pledge(self):
        """Test creating pledge"""
        data = {
            'member': self.member.id,
            'amount': '500.00',
            'frequency': 'weekly',
            'start_date': timezone.now().date().isoformat(),
            'status': 'active'
        }
        
        response = self.admin_client.post('/api/v1/pledges/', data)
        
        self.assertCreated(response)
        self.assertEqual(response.data['frequency'], 'weekly')

