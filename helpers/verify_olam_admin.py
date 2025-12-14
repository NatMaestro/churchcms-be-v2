"""
Quick script to verify and create admin user for olamchurch.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.churches.models import Church
from django_tenants.utils import schema_context

User = get_user_model()

# Get olamchurch tenant
church = Church.objects.get(subdomain='olamchurch')
print(f"\n✅ Found church: {church.name} (schema: {church.schema_name})\n")

# Check users in tenant schema
with schema_context(church.schema_name):
    email = 'nathanielgugisberg@gmail.com'
    
    try:
        user = User.objects.get(email=email)
        print(f"✅ User found:")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.name}")
        print(f"   Role: {user.role}")
        print(f"   Is Active: {user.is_active}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"   Church ID: {user.church_id}")
        print(f"\n💡 If login is failing, check:")
        print(f"   1. Password is correct")
        print(f"   2. User is active: {user.is_active}")
        print(f"   3. User belongs to church: {user.church_id == church.id}")
    except User.DoesNotExist:
        print(f"❌ User '{email}' NOT FOUND in olamchurch tenant!")
        print(f"\nCreating user...")
        
        user = User.objects.create(
            email=email,
            name='Nathaniel Gugisberg',
            role='admin',
            is_staff=True,
            is_active=True,
            church=church
        )
        user.set_password('olam@church')
        user.save()
        
        print(f"✅ User created successfully!")
        print(f"   Email: {user.email}")
        print(f"   Password: olam@church")
        print(f"   Role: {user.role}")



