"""
Verify announcements table exists and is accessible.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.churches.models import Church
from apps.announcements.models import Announcement

def verify_announcements(subdomain):
    """Verify announcements table and model."""
    try:
        church = Church.objects.get(subdomain=subdomain)
        print(f"Found church: {church.name} (schema: {church.schema_name})")
        
        # Switch to tenant schema
        connection.set_tenant(church)
        print(f"Switched to tenant schema: {church.schema_name}")
        
        # Check table exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = current_schema() 
                AND table_name = 'announcements'
            """)
            table_exists = bool(cursor.fetchone())
            print(f"Table 'announcements' exists: {table_exists}")
        
        # Try to query using ORM
        try:
            count = Announcement.objects.count()
            print(f"✅ ORM query successful - Found {count} announcement(s)")
            
            # Try to get all announcements
            announcements = Announcement.objects.all()[:5]
            print(f"✅ Retrieved {len(announcements)} announcement(s) via ORM")
            for ann in announcements:
                print(f"  - {ann.title} (ID: {ann.id})")
        except Exception as e:
            print(f"❌ ORM query failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Switch back to public
        connection.set_schema_to_public()
        
    except Church.DoesNotExist:
        print(f"❌ Church with subdomain '{subdomain}' not found")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        connection.set_schema_to_public()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python verify_announcements.py <subdomain>")
        sys.exit(1)
    
    subdomain = sys.argv[1]
    verify_announcements(subdomain)

