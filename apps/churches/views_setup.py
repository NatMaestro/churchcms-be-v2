"""
Setup views for initial church creation (for environments without shell access)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.db import connection
import os

from apps.churches.models import Church, Domain
from apps.authentication.models import User


class InitialSetupView(APIView):
    """
    Create initial church and admin user
    Only works if no churches exist yet (safety measure)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Create initial church setup
        
        Body:
        {
            "church_name": "My Church",
            "subdomain": "mychurch",
            "email": "info@mychurch.com",
            "admin_name": "Admin User",
            "admin_email": "admin@mychurch.com",
            "admin_password": "securepassword",
            "setup_token": "your-secret-setup-token"
        }
        """
        # Verify setup token for security
        setup_token = request.data.get('setup_token')
        expected_token = os.getenv('SETUP_TOKEN', settings.SECRET_KEY[:32])
        
        if setup_token != expected_token:
            return Response(
                {'error': 'Invalid setup token'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if churches already exist (safety)
        existing_churches = Church.objects.exclude(schema_name='public').count()
        if existing_churches > 0:
            return Response(
                {
                    'error': 'Setup already completed',
                    'message': f'{existing_churches} church(es) already exist'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get data from request
        church_name = request.data.get('church_name')
        subdomain = request.data.get('subdomain')
        email = request.data.get('email')
        denomination = request.data.get('denomination', '')
        
        admin_name = request.data.get('admin_name')
        admin_email = request.data.get('admin_email')
        admin_password = request.data.get('admin_password')
        
        # Validate required fields
        required_fields = {
            'church_name': church_name,
            'subdomain': subdomain,
            'email': email,
            'admin_name': admin_name,
            'admin_email': admin_email,
            'admin_password': admin_password,
        }
        
        missing_fields = [k for k, v in required_fields.items() if not v]
        if missing_fields:
            return Response(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create church
            church = Church.objects.create(
                schema_name=subdomain,
                name=church_name,
                subdomain=subdomain,
                email=email,
                denomination=denomination,
                plan='trial',
                is_active=True
            )
            
            # Create domains
            # For Render deployment
            Domain.objects.create(
                domain=f'{subdomain}.faithflow-backend.onrender.com',
                tenant=church,
                is_primary=True
            )
            
            # For custom domain (if configured)
            if settings.DEBUG is False:
                Domain.objects.create(
                    domain=f'{subdomain}.faithflows.com',
                    tenant=church,
                    is_primary=False
                )
            
            # Switch to tenant schema
            connection.set_tenant(church)
            
            # Create admin user
            admin_user = User.objects.create_user(
                email=admin_email,
                password=admin_password,
                name=admin_name,
                church=church,
                role='admin',
                is_active=True
            )
            
            return Response({
                'success': True,
                'message': 'Initial setup complete!',
                'church': {
                    'name': church.name,
                    'subdomain': church.subdomain,
                    'schema': church.schema_name,
                },
                'admin': {
                    'name': admin_user.name,
                    'email': admin_user.email,
                },
                'urls': {
                    'api': f'https://{subdomain}.faithflow-backend.onrender.com/api/docs/',
                    'login': f'https://{subdomain}.faithflow-backend.onrender.com/api/v1/auth/login/',
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

