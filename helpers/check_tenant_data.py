"""
Check data in tenant schema
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context, get_tenant_model
from apps.churches.models import Church
from apps.authentication.models import User
from apps.members.models import Member
from apps.events.models import Event
from apps.payments.models import Payment

def check_tenant_data(tenant_name):
    """Check what data exists in a tenant schema."""
    try:
        church = Church.objects.get(schema_name=tenant_name)
        print(f"\n{'='*60}")
        print(f"Checking data for: {church.name} ({church.subdomain})")
        print(f"{'='*60}")
        
        # Switch to tenant schema
        with schema_context(church.schema_name):
            # Check Users
            users = User.objects.all()
            print(f"\n📊 Users: {users.count()}")
            for user in users[:5]:
                print(f"   - {user.email} ({user.role}) - Church: {user.church}")
            
            # Check Members
            members = Member.objects.all()
            print(f"\n👥 Members: {members.count()}")
            for member in members[:5]:
                print(f"   - {member.first_name} {member.last_name} ({member.member_id})")
            
            # Check Events
            events = Event.objects.all()
            print(f"\n📅 Events: {events.count()}")
            for event in events[:5]:
                print(f"   - {event.title} ({event.date})")
            
            # Check Payments
            payments = Payment.objects.all()
            print(f"\n💰 Payments: {payments.count()}")
            for payment in payments[:5]:
                print(f"   - {payment.reference} - ${payment.amount}")
        
        print(f"\n{'='*60}\n")
        
    except Church.DoesNotExist:
        print(f"❌ Church with schema '{tenant_name}' not found!")
        print("\nAvailable churches:")
        for church in Church.objects.all():
            print(f"   - {church.name} (schema: {church.schema_name}, subdomain: {church.subdomain})")

if __name__ == "__main__":
    # Check all churches
    print("\n🔍 Checking all tenant data...")
    
    churches = Church.objects.exclude(schema_name='public')
    
    if not churches.exists():
        print("❌ No churches found! Run seed_one_church.py first.")
    else:
        for church in churches:
            check_tenant_data(church.schema_name)




