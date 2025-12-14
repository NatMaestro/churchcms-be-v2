"""
Church views with subdomain resolution and feature management.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Church, Domain
from .serializers import ChurchSerializer, ChurchDetailSerializer, DomainSerializer
from core.permissions import IsSuperAdmin, IsChurchAdmin


class ChurchViewSet(viewsets.ModelViewSet):
    """
    Church management viewset.
    """
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve."""
        if self.action == 'retrieve':
            return ChurchDetailSerializer
        return ChurchSerializer
    
    def get_queryset(self):
        """Filter churches based on user role."""
        user = self.request.user
        if user.is_superadmin:
            return Church.objects.all()
        elif user.church:
            return Church.objects.filter(id=user.church.id)
        return Church.objects.none()
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def by_subdomain(self, request):
        """
        Get church by subdomain.
        Public endpoint for subdomain resolution.
        
        GET /api/v1/churches/by-subdomain/?subdomain=olamchurch
        """
        subdomain = request.query_params.get('subdomain')
        
        if not subdomain:
            return Response({
                'success': False,
                'error': 'Subdomain parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            church = Church.objects.get(subdomain=subdomain, is_active=True)
            serializer = ChurchDetailSerializer(church)
            
            return Response({
                'success': True,
                'church': serializer.data
            })
        except Church.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Church not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def validate_subdomain(self, request):
        """
        Validate if subdomain is available.
        
        POST /api/v1/churches/validate-subdomain/
        Body: { "subdomain": "newchurch" }
        """
        subdomain = request.data.get('subdomain', '').lower().strip()
        
        if not subdomain:
            return Response({
                'success': False,
                'available': False,
                'error': 'Subdomain is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if subdomain already exists
        exists = Church.objects.filter(subdomain=subdomain).exists()
        
        # Validate subdomain format
        import re
        is_valid = bool(re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', subdomain))
        
        # Reserved subdomains
        reserved = ['www', 'api', 'admin', 'app', 'mail', 'ftp', 'superadmin']
        is_reserved = subdomain in reserved
        
        return Response({
            'success': True,
            'available': not exists and is_valid and not is_reserved,
            'exists': exists,
            'valid_format': is_valid,
            'reserved': is_reserved
        })
    
    @action(detail=True, methods=['get', 'put'])
    def features(self, request, pk=None):
        """
        Get or update church features.
        
        GET /api/v1/churches/:id/features/
        PUT /api/v1/churches/:id/features/
        """
        church = self.get_object()
        
        # Check permissions
        if not (request.user.is_superadmin or 
                (request.user.church and request.user.church.id == church.id and request.user.is_church_admin)):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if request.method == 'GET':
            return Response({
                'success': True,
                'features': church.get_default_features()
            })
        
        elif request.method == 'PUT':
            # Update features
            new_features = request.data.get('features', {})
            church.features = {**church.features, **new_features}
            church.save()
            
            return Response({
                'success': True,
                'message': 'Features updated successfully',
                'features': church.features
            })
    
    @action(detail=True, methods=['get', 'put'])
    def church_settings(self, request, pk=None):
        """
        Get or update church settings.
        
        GET /api/v1/churches/:id/church-settings/
        PUT /api/v1/churches/:id/church-settings/
        """
        church = self.get_object()
        
        if request.method == 'GET':
            return Response({
                'success': True,
                'settings': {
                    'branding': church.branding_settings,
                    'payment': church.payment_settings,
                    'member': church.member_settings,
                    'communication': church.communication_settings,
                    'privacy': church.privacy_settings,
                    'automation': church.automation_settings,
                    'integration': church.integration_settings,
                }
            })
        
        elif request.method == 'PUT':
            # Update specific settings
            settings_type = request.data.get('type')
            settings_data = request.data.get('data', {})
            
            if settings_type == 'branding':
                church.branding_settings = {**church.branding_settings, **settings_data}
            elif settings_type == 'payment':
                church.payment_settings = {**church.payment_settings, **settings_data}
            elif settings_type == 'member':
                church.member_settings = {**church.member_settings, **settings_data}
            elif settings_type == 'communication':
                church.communication_settings = {**church.communication_settings, **settings_data}
            elif settings_type == 'privacy':
                church.privacy_settings = {**church.privacy_settings, **settings_data}
            elif settings_type == 'automation':
                church.automation_settings = {**church.automation_settings, **settings_data}
            elif settings_type == 'integration':
                church.integration_settings = {**church.integration_settings, **settings_data}
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid settings type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            church.save()
            
            return Response({
                'success': True,
                'message': f'{settings_type.capitalize()} settings updated successfully'
            })
    
    @action(detail=True, methods=['post'])
    def apply_denomination_defaults(self, request, pk=None):
        """
        Apply denomination-specific feature defaults to church.
        
        POST /api/v1/churches/:id/apply-denomination-defaults/
        """
        church = self.get_object()
        
        # Get defaults for denomination
        defaults = church.get_default_features()
        
        # Apply defaults
        church.features = defaults
        church.save()
        
        return Response({
            'success': True,
            'message': 'Denomination defaults applied successfully',
            'features': church.features
        })
