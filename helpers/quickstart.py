"""
Quick start script for FaithFlow Studio Backend.
Run this after initial setup to create first church and admin.

Usage:
    python quickstart.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.churches.models import Church, Domain
from apps.authentication.models import User
from django.db import connection


def create_first_church():
    """Create the first church tenant."""
    
    print("\n" + "="*60)
    print("FaithFlow Studio - Quick Start Setup")
    print("="*60 + "\n")
    
    # Get church details
    print("Let's create your first church!\n")
    
    church_name = input("Church Name: ")
    subdomain = input("Subdomain (lowercase, no spaces): ").lower().replace(' ', '')
    email = input("Church Email: ")
    denomination = input("Denomination (Catholic/Pentecostal/etc): ")
    
    # Create church
    print("\n Creating church...")
    church = Church.objects.create(
        schema_name=subdomain,
        name=church_name,
        subdomain=subdomain,
        email=email,
        denomination=denomination,
        plan='trial',
        is_active=True
    )
    print(f"✅ Church created: {church.name} (Schema: {church.schema_name})")
    
    # Create domain
    print("\nCreating domain...")
    domain = Domain.objects.create(
        domain=f"{subdomain}.localhost",  # For development
        tenant=church,
        is_primary=True
    )
    print(f"✅ Domain created: {domain.domain}")
    
    # Create admin user
    print("\nCreating admin user...")
    admin_name = input("Admin Name: ")
    admin_email = input("Admin Email: ")
    admin_password = input("Admin Password: ")
    
    # Switch to tenant schema
    connection.set_tenant(church)
    
    admin = User.objects.create_user(
        email=admin_email,
        password=admin_password,
        name=admin_name,
        church=church,
        role='admin',
        is_active=True
    )
    print(f"✅ Admin user created: {admin.email}")
    
    # Summary
    print("\n" + "="*60)
    print("Setup Complete! 🎉")
    print("="*60)
    print(f"\nChurch: {church.name}")
    print(f"Subdomain: {subdomain}")
    print(f"URL: http://{subdomain}.localhost:8000")
    print(f"\nAdmin Login:")
    print(f"  Email: {admin_email}")
    print(f"  Password: {admin_password}")
    print(f"\nNext steps:")
    print("1. python manage.py runserver")
    print(f"2. Visit http://{subdomain}.localhost:8000/api/docs/")
    print("3. Login with admin credentials")
    print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    try:
        create_first_church()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Created .env file with database settings")
        print("2. Run: python manage.py migrate_schemas --shared")
        print("3. Run: python manage.py migrate_schemas")




