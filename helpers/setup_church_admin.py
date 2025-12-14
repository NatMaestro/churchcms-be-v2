"""
Setup church admin user in tenant schema.
This creates the church owner/admin who manages the church.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.churches.models import Church
from django_tenants.utils import schema_context

User = get_user_model()

def setup_church_admin():
    """Create or update church admin user."""
    
    print("\n" + "="*70)
    print("🏛️  CHURCH ADMIN SETUP")
    print("="*70)
    print("\nThis creates the church owner/admin who manages the church.")
    print("This is different from the platform superuser.\n")
    
    # Show available churches
    print("Available churches:")
    churches = Church.objects.exclude(schema_name='public')
    for idx, c in enumerate(churches, 1):
        print(f"  {idx}. {c.name} ({c.subdomain})")
    
    church_choice = input(f"\nSelect church (1-{churches.count()}): ").strip()
    church = list(churches)[int(church_choice) - 1]
    
    print(f"\n✅ Selected: {church.name} (schema: {church.schema_name})")
    print(f"   Subdomain: {church.subdomain}")
    print(f"   Login URL: http://{church.subdomain}.localhost:8000/api/v1/auth/login/")
    
    # Get admin details
    print("\n" + "-"*70)
    print("CHURCH ADMIN DETAILS")
    print("-"*70)
    
    email = input("Email: ").strip()
    
    # Check if user exists
    with schema_context(church.schema_name):
        existing_user = User.objects.filter(email=email).first()
        
        if existing_user:
            print(f"\n⚠️  User '{email}' already exists in {church.name}")
            print(f"   Current role: {existing_user.role}")
            print(f"   Is staff: {existing_user.is_staff}")
            print(f"   Is active: {existing_user.is_active}")
            
            action = input("\nWhat would you like to do?\n  1. Update password\n  2. Update role to admin\n  3. Update both\n  4. Skip\nChoice (1-4): ").strip()
            
            if action in ['1', '3']:
                password = input("New password: ").strip()
                existing_user.set_password(password)
                print("✅ Password updated")
            
            if action in ['2', '3']:
                existing_user.role = 'admin'
                existing_user.is_staff = True
                print("✅ Role updated to admin")
            
            if action != '4':
                existing_user.save()
                print(f"\n✅ User updated successfully!")
            
            return
        
        # Create new user
        name = input("Full Name: ").strip()
        password = input("Password: ").strip()
        
        user = User.objects.create(
            email=email,
            name=name,
            role='admin',  # Church admin role
            is_staff=True,  # Can access Django admin
            is_active=True,
            church=church
        )
        user.set_password(password)
        user.save()
        
        print("\n" + "="*70)
        print("✅ CHURCH ADMIN CREATED SUCCESSFULLY!")
        print("="*70)
        print(f"\nChurch: {church.name}")
        print(f"Subdomain: {church.subdomain}")
        print(f"\n👤 ADMIN DETAILS:")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.name}")
        print(f"   Role: {user.role}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"\n🔐 LOGIN CREDENTIALS:")
        print(f"   URL: http://{church.subdomain}.localhost:8080/admin")
        print(f"   Email: {user.email}")
        print(f"   Password: {password}")
        print(f"\n📝 API LOGIN:")
        print(f"   POST http://{church.subdomain}.localhost:8000/api/v1/auth/login/")
        print(f"   Body: {{'email': '{user.email}', 'password': '{password}'}}")
        print("="*70)

if __name__ == '__main__':
    setup_church_admin()



