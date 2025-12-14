"""
Script to check if Olam church has data seeded
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context
from apps.churches.models import Church, Domain
from apps.authentication.models import User
from apps.members.models import Member
from apps.events.models import Event
from apps.payments.models import Payment
from apps.themes.models import Theme
from apps.announcements.models import Announcement

def check_olam_data():
    """Check if Olam church has data"""
    
    try:
        # Find Olam church
        olam = Church.objects.filter(subdomain='olamchurch').first()
        
        if not olam:
            print("❌ Olam church not found!")
            print("\nAvailable churches:")
            for church in Church.objects.all():
                print(f"  - {church.name} (subdomain: {church.subdomain}, schema: {church.schema_name})")
            return
        
        print(f"✅ Found Olam church:")
        print(f"   Name: {olam.name}")
        print(f"   Subdomain: {olam.subdomain}")
        print(f"   Schema: {olam.schema_name}")
        print(f"   Active: {olam.is_active}")
        
        # Check domains
        domains = Domain.objects.filter(tenant=olam)
        print(f"\n📍 Domains ({domains.count()}):")
        for domain in domains:
            print(f"   - {domain.domain} (primary: {domain.is_primary})")
        
        # Switch to Olam's schema and check data
        with schema_context(olam.schema_name):
            # Check users
            users = User.objects.all()
            print(f"\n👥 Users: {users.count()}")
            for user in users[:5]:  # Show first 5
                print(f"   - {user.email} (role: {user.role})")
            
            # Check members
            members = Member.objects.all()
            print(f"\n👤 Members: {members.count()}")
            for member in members[:5]:  # Show first 5
                print(f"   - {member.first_name} {member.surname} ({member.email})")
            
            # Check events
            events = Event.objects.all()
            print(f"\n📅 Events: {events.count()}")
            for event in events[:5]:  # Show first 5
                print(f"   - {event.title} (date: {event.date})")
            
            # Check payments
            payments = Payment.objects.all()
            print(f"\n💰 Payments: {payments.count()}")
            for payment in payments[:5]:  # Show first 5
                print(f"   - {payment.reference} (amount: {payment.amount}, status: {payment.status})")
            
            # Check themes
            themes = Theme.objects.all()
            print(f"\n🎨 Themes: {themes.count()}")
            for theme in themes[:5]:  # Show first 5
                print(f"   - {theme.name} (active: {theme.is_active})")
            
            # Check announcements
            announcements = Announcement.objects.all()
            print(f"\n📢 Announcements: {announcements.count()}")
            for announcement in announcements[:5]:  # Show first 5
                print(f"   - {announcement.title}")
        
        print("\n" + "="*60)
        print("Summary:")
        print("="*60)
        with schema_context(olam.schema_name):
            print(f"Users:         {User.objects.count()}")
            print(f"Members:       {Member.objects.count()}")
            print(f"Events:        {Event.objects.count()}")
            print(f"Payments:      {Payment.objects.count()}")
            print(f"Themes:        {Theme.objects.count()}")
            print(f"Announcements: {Announcement.objects.count()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_olam_data()
