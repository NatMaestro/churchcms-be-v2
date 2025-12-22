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
    
    @action(detail=True, methods=['post'])
    def start_trial(self, request, pk=None):
        """
        Start a 30-day trial for the church.
        
        POST /api/v1/churches/:id/start-trial/
        """
        from django.utils import timezone
        from datetime import timedelta
        
        church = self.get_object()
        
        # Check permissions
        if not (request.user.is_superadmin or 
                (request.user.church and request.user.church.id == church.id and request.user.is_church_admin)):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Set trial dates
        now = timezone.now()
        trial_end = now + timedelta(days=30)
        
        church.plan = 'trial'
        church.subscription_status = 'active'
        church.trial_started_at = now
        church.trial_end_date = trial_end
        church.save()
        
        return Response({
            'success': True,
            'message': 'Trial started successfully',
            'trial_started_at': church.trial_started_at,
            'trial_end_date': church.trial_end_date,
            'days_remaining': 30
        })
    
    @action(detail=True, methods=['post'], url_path='upgrade-subscription', url_name='upgrade-subscription')
    def upgrade_subscription(self, request, pk=None):
        """
        Upgrade church subscription to a paid plan.
        
        POST /api/v1/churches/:id/upgrade-subscription/
        Body: {
            "plan": "basic|standard|premium|enterprise",
            "duration": "monthly|yearly"
        }
        """
        from django.utils import timezone
        from datetime import timedelta
        
        church = self.get_object()
        
        # Check permissions
        if not (request.user.is_superadmin or 
                (request.user.church and request.user.church.id == church.id and request.user.is_church_admin)):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        plan = request.data.get('plan')
        duration = request.data.get('duration', 'monthly')
        
        if plan not in ['basic', 'standard', 'premium', 'enterprise']:
            return Response({
                'success': False,
                'error': 'Invalid plan. Must be: basic, standard, premium, or enterprise'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate subscription dates
        now = timezone.now()
        if duration == 'yearly':
            subscription_end = now + timedelta(days=365)
        else:
            subscription_end = now + timedelta(days=30)
        
        # Log before update
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔄 Upgrading subscription for church {church.id} ({church.subdomain})")
        logger.info(f"   Plan: {plan}, Duration: {duration}")
        logger.info(f"   Setting dates - Start: {now}, End: {subscription_end}")
        logger.info(f"   Before update - Plan: {church.plan}, Start: {church.subscription_start_date}, End: {church.subscription_end_date}")
        
        # Update church subscription fields
        church.plan = plan
        church.subscription_status = 'active'
        church.subscription_start_date = now
        church.subscription_end_date = subscription_end
        # Clear trial if upgrading from trial
        church.trial_end_date = None
        
        # Save the church - django-tenants should handle schema switching automatically
        # since Church is a TenantMixin model in the public schema
        church.save(update_fields=['plan', 'subscription_status', 'subscription_start_date', 'subscription_end_date', 'trial_end_date'])
        
        # Refresh to ensure we have the latest data
        church.refresh_from_db()
        
        logger.info(f"   ✅ After save - Plan: {church.plan}, Start: {church.subscription_start_date}, End: {church.subscription_end_date}")
        
        return Response({
            'success': True,
            'message': f'Subscription upgraded to {plan} plan',
            'plan': church.plan,
            'subscription_start_date': church.subscription_start_date,
            'subscription_end_date': church.subscription_end_date,
            'duration': duration
        })
    
    @action(detail=True, methods=['get'])
    def subscription_status(self, request, pk=None):
        """
        Get current subscription status and details.
        
        GET /api/v1/churches/:id/subscription-status/
        """
        church = self.get_object()
        
        # Check permissions
        if not (request.user.is_superadmin or 
                (request.user.church and request.user.church.id == church.id)):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        status_info = church.get_subscription_status()
        days_remaining = church.get_days_until_expiration()
        can_access = church.can_access_system()
        
        return Response({
            'success': True,
            'plan': church.plan,
            'subscription_status': church.subscription_status,
            'status': status_info,
            'can_access': can_access,
            'days_remaining': days_remaining,
            'trial_started_at': church.trial_started_at,
            'trial_end_date': church.trial_end_date,
            'subscription_start_date': church.subscription_start_date,
            'subscription_end_date': church.subscription_end_date,
            'grace_period_days': church.grace_period_days,
            'bypass_subscription_check': church.bypass_subscription_check,
        })