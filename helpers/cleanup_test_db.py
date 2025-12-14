"""
Clean up test database connections
"""
import os
import sys
import django
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def cleanup_test_db():
    """Terminate connections to test database"""
    with connection.cursor() as cursor:
        # Terminate all connections to test database
        cursor.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'test_neondb'
            AND pid <> pg_backend_pid();
        """)
        
        print("✅ Terminated connections to test database")
        
        # Drop test database
        try:
            cursor.execute("DROP DATABASE IF EXISTS test_neondb;")
            print("✅ Dropped test database")
        except Exception as e:
            print(f"⚠️  Could not drop database: {e}")

if __name__ == '__main__':
    cleanup_test_db()




