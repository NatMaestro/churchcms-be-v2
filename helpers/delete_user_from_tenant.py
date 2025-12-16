"""
Helper script to delete a user from a specific tenant schema.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure Django BEFORE importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# Now import models after Django is configured
from django.db import connection
from apps.churches.models import Church
from apps.authentication.models import User

def delete_user_from_tenant(subdomain, email):
    """Delete a user from a specific tenant schema."""
    try:
        church = Church.objects.get(subdomain=subdomain)
        connection.set_tenant(church)
        
        user = User.objects.filter(email=email).first()
        if user:
            print(f"Found user in {subdomain} tenant:")
            print(f"  ID: {user.id}")
            print(f"  Name: {user.name}")
            print(f"  Email: {user.email}")
            print(f"  Church: {user.church.name if user.church else None}")
            
            user.delete()
            print(f"✅ Deleted user {email} from {subdomain} tenant schema")
        else:
            print(f"❌ User with email {email} not found in {subdomain} tenant schema")
        
        connection.set_schema_to_public()
    except Church.DoesNotExist:
        print(f"❌ Church with subdomain '{subdomain}' not found")
    except Exception as e:
        print(f"❌ Error: {e}")
        connection.set_schema_to_public()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python delete_user_from_tenant.py <subdomain> <email>")
        sys.exit(1)
    
    subdomain = sys.argv[1]
    email = sys.argv[2]
    delete_user_from_tenant(subdomain, email)

