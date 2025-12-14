"""
Create Django superuser for admin panel access
"""
import os
import sys
import django
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection

# Use the public schema for superuser
connection.set_schema_to_public()

User = get_user_model()

# Check if superuser already exists
if User.objects.filter(email='superadmin@faithflows.com').exists():
    print("\n✅ Superuser already exists!")
    print("   Email: superadmin@faithflows.com")
    print("\n   To reset password, delete the user and run this script again.")
else:
    print("\n🔧 Creating Django Superuser...")
    print("="*60)
    
    email = input("Email (default: superadmin@faithflows.com): ") or "superadmin@faithflows.com"
    name = input("Name (default: Super Admin): ") or "Super Admin"
    password = input("Password: ")
    
    if not password:
        print("\n❌ Password cannot be empty!")
        sys.exit(1)
    
    # Create superuser
    user = User.objects.create_superuser(
        email=email,
        password=password,
        name=name,
        church=None,  # Superuser doesn't belong to a specific church
        role='superadmin'
    )
    
    print("\n" + "="*60)
    print("✅ SUPERUSER CREATED!")
    print("="*60)
    print(f"\nEmail: {email}")
    print(f"Name: {name}")
    print("\n🌐 Access Django Admin:")
    print("   http://localhost:8000/admin/")
    print("\n   You can see ALL churches, users, and data!")
    print("\n")




