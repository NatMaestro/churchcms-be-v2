"""
Create a user in a specific tenant schema.
Usage: python create_tenant_user.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.churches.models import Church
from django_tenants.utils import schema_context

User = get_user_model()

def create_tenant_user():
    """Create a user in a tenant schema."""
    
    # Get tenant details from user
    tenant_subdomain = input("Enter tenant subdomain (e.g., 'olamchurch'): ").strip()
    
    try:
        church = Church.objects.get(subdomain=tenant_subdomain)
        print(f"\n✅ Found church: {church.name} (schema: {church.schema_name})")
    except Church.DoesNotExist:
        print(f"\n❌ No church found with subdomain '{tenant_subdomain}'")
        print("\nAvailable churches:")
        for c in Church.objects.exclude(schema_name='public'):
            print(f"  - {c.subdomain} ({c.name})")
        return
    
    # Get user details
    print("\n" + "="*60)
    print("CREATE USER FOR TENANT")
    print("="*60)
    
    email = input("Email: ").strip()
    name = input("Full Name: ").strip()
    password = input("Password: ").strip()
    role = input("Role (admin/pastor/staff/member) [admin]: ").strip() or 'admin'
    is_staff = input("Is staff (can access Django admin)? (y/n) [y]: ").strip().lower() != 'n'
    
    # Create user in tenant schema
    with schema_context(church.schema_name):
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            print(f"\n❌ User with email '{email}' already exists in {church.name}")
            update = input("Update password? (y/n): ").strip().lower()
            if update == 'y':
                user = User.objects.get(email=email)
                user.set_password(password)
                user.name = name
                user.role = role
                user.is_staff = is_staff
                user.church = church
                user.save()
                print(f"\n✅ User updated successfully!")
            return
        
        # Create new user
        user = User.objects.create(
            email=email,
            name=name,
            role=role,
            is_staff=is_staff,
            is_active=True,
            church=church
        )
        user.set_password(password)
        user.save()
        
        print("\n" + "="*60)
        print("✅ USER CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"Tenant: {church.name} ({church.subdomain})")
        print(f"Schema: {church.schema_name}")
        print(f"Email: {user.email}")
        print(f"Name: {user.name}")
        print(f"Role: {user.role}")
        print(f"Is Staff: {user.is_staff}")
        print(f"Church ID: {user.church_id}")
        print("\n📝 LOGIN DETAILS:")
        print(f"   URL: http://{church.subdomain}.localhost:8000/api/v1/auth/login/")
        print(f"   Email: {user.email}")
        print(f"   Password: {password}")
        print("="*60)

if __name__ == '__main__':
    create_tenant_user()



