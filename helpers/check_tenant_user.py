"""
Check if a user exists in a tenant schema.
Usage: python check_tenant_user.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.churches.models import Church
from django_tenants.utils import schema_context

User = get_user_model()

def check_user():
    """Check if user exists in tenant."""
    email = input("Enter email to check: ").strip()
    tenant_subdomain = input("Enter tenant subdomain (e.g., 'olamchurch'): ").strip() or 'olamchurch'
    
    try:
        church = Church.objects.get(subdomain=tenant_subdomain)
        print(f"\n✅ Found church: {church.name} (schema: {church.schema_name})")
    except Church.DoesNotExist:
        print(f"\n❌ No church found with subdomain '{tenant_subdomain}'")
        return
    
    # Check in tenant schema
    with schema_context(church.schema_name):
        try:
            user = User.objects.get(email=email)
            print("\n" + "="*60)
            print("✅ USER FOUND!")
            print("="*60)
            print(f"Email: {user.email}")
            print(f"Name: {user.name}")
            print(f"Role: {user.role}")
            print(f"Is Active: {user.is_active}")
            print(f"Is Staff: {user.is_staff}")
            print(f"Church ID: {user.church_id}")
            print(f"Church Name: {user.church.name if user.church else 'None'}")
            print("="*60)
        except User.DoesNotExist:
            print(f"\n❌ User '{email}' NOT FOUND in {church.name} tenant")
            print("\nChecking all users in this tenant...")
            users = User.objects.all()
            if users.exists():
                print(f"\nFound {users.count()} users:")
                for u in users:
                    print(f"  - {u.email} ({u.name}) - Role: {u.role} - Active: {u.is_active}")
            else:
                print("  No users found in this tenant schema.")

if __name__ == '__main__':
    check_user()



