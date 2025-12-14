"""
Test API responses for tenant data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context
from apps.churches.models import Church
from apps.authentication.models import User
from django.test import RequestFactory
from rest_framework.test import force_authenticate
from apps.members.views import MemberViewSet

def test_member_api():
    """Test member API responses."""
    try:
        church = Church.objects.get(subdomain='olamchurch')
        print(f"\n✅ Found church: {church.name}")
        
        # Switch to tenant schema
        with schema_context(church.schema_name):
            # Get a user
            user = User.objects.filter(church=church).first()
            if not user:
                print("❌ No user found for Olam Church!")
                return
            
            print(f"✅ Found user: {user.email} (Role: {user.role})")
            print(f"   User's church: {user.church.name if user.church else 'None'}")
            
            # Create a fake request
            factory = RequestFactory()
            request = factory.get('/api/v1/members/')
            request.user = user
            
            # Set HTTP_HOST for tenant middleware
            request.META['HTTP_HOST'] = f'{church.subdomain}.localhost:8000'
            
            # Test MemberViewSet
            view = MemberViewSet.as_view({'get': 'list'})
            force_authenticate(request, user=user)
            
            response = view(request)
            
            print(f"\n📊 API Response:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Data: {response.data if response.status_code == 200 else 'Error'}")
            
    except Church.DoesNotExist:
        print("❌ Olam Church not found!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n🔍 Testing API responses...")
    test_member_api()




