"""
Quick script to check user in olamchurch tenant.
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
    users = User.objects.all()
    if users.exists():
        print(f"Found {users.count()} user(s) in olamchurch tenant:\n")
        for u in users:
            print(f"  Email: {u.email}")
            print(f"  Name: {u.name}")
            print(f"  Role: {u.role}")
            print(f"  Is Active: {u.is_active}")
            print(f"  Is Staff: {u.is_staff}")
            print(f"  Church ID: {u.church_id}")
            print("-" * 50)
    else:
        print("❌ No users found in olamchurch tenant schema!")



