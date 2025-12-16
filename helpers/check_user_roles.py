#!/usr/bin/env python
"""
Check user roles across all tenants.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User
from apps.churches.models import Church
from apps.roles.models import Role, UserRole
from django.db import connection

def check_user_roles(email):
    """Check user roles across all tenants."""
    connection.set_schema_to_public()
    
    print('=== All Churches ===')
    churches = Church.objects.all()
    for church in churches:
        print(f'  {church.id}: {church.name} (subdomain: {church.subdomain})')
    
    print(f'\n=== Checking user: {email} ===')
    for church in churches:
        connection.set_tenant(church)
        user = User.objects.filter(email=email).first()
        if user:
            print(f'\n✅ Found in {church.name} (subdomain: {church.subdomain}):')
            print(f'   User ID: {user.id}')
            print(f'   User Name: {user.name}')
            print(f'   User Role: {user.role}')
            print(f'   Church ID: {user.church_id}')
            
            roles = Role.objects.all()
            print(f'   Roles in this tenant: {roles.count()}')
            for r in roles:
                print(f'     - {r.name} (ID: {r.id})')
            
            user_roles = UserRole.objects.filter(user=user, is_active=True)
            print(f'   User role assignments (active): {user_roles.count()}')
            for ur in user_roles:
                print(f'     - {ur.role.name} (Role ID: {ur.role.id}, Active: {ur.is_active})')
            
            if user_roles.count() == 0:
                print('   ⚠️  User has NO assigned roles!')
        
        connection.set_schema_to_public()

if __name__ == '__main__':
    email = sys.argv[1] if len(sys.argv) > 1 else 'nathanielguggisberg@gmail.com'
    check_user_roles(email)





