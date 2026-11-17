"""
Church views with subdomain resolution and feature management.
"""

import logging

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from . import subscriptions
from .models import Church, Domain
from .serializers import ChurchSerializer, ChurchDetailSerializer, DomainSerializer, PublicChurchSerializer
from core.member_context import is_church_staff
from core.permissions import IsSuperAdmin, IsChurchAdmin
from .giving_details import GivingDetailsSerializer, read_giving_details, save_giving_details

logger = logging.getLogger(__name__)

# Church changes a church admin (of that church) or a platform superadmin may make.
CHURCH_ADMIN_WRITE_ACTIONS = ('update', 'partial_update', 'church_settings', 'apply_denomination_defaults',
                              'giving_details')


class IsChurchStaff(permissions.BasePermission):
    message = 'Only the church admin can change the church.'

    def has_permission(self, request, view):
        return is_church_staff(request.user)


BILLING_HISTORY_LIMIT = 24


class ChurchViewSet(viewsets.ModelViewSet):
    """
    Church management viewset.
    """
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """
        Reading the church is open to its people; changing it is for its admin
        (the queryset limits admins to their own church); creating or deleting
        a church is for platform superadmins.
        """
        if self.action in ('create', 'destroy'):
            return [permissions.IsAuthenticated(), IsSuperAdmin()]
        if self.action == 'church_settings':
            # Holds integration secrets (e.g. a stream key): staff only, reading included.
            return [permissions.IsAuthenticated(), IsChurchStaff()]
        if self.action in CHURCH_ADMIN_WRITE_ACTIONS and self.request.method not in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated(), IsChurchStaff()]
        return super().get_permissions()

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
        
        GET /api/v1/churches/by_subdomain/?subdomain=olamchurch

        Unauthenticated, so it returns only the public profile.
        """
        subdomain = request.query_params.get('subdomain')
        
        if not subdomain:
            return Response({
                'success': False,
                'error': 'Subdomain parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            church = Church.objects.get(subdomain=subdomain, is_active=True)
            serializer = PublicChurchSerializer(church)
            
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
    
    @action(detail=True, methods=['get', 'put'], url_path='giving-details', url_name='giving-details')
    def giving_details(self, request, pk=None):
        """
        The church's Mobile Money and bank details for members who give directly.

        GET /api/v1/churches/:id/giving-details/  (anyone in the church)
        PUT /api/v1/churches/:id/giving-details/  (the church admin; replaces all fields)
        """
        church = self.get_object()
        if request.method == 'GET':
            return Response(read_giving_details(church))

        serializer = GivingDetailsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        details = save_giving_details(church, serializer.validated_data, request.user)
        logger.info('church_giving_details_updated', extra={'church_id': church.pk, 'actor_id': request.user.pk})
        return Response(details)

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
    
    @action(detail=True, methods=['post'], url_path='start-trial', url_name='start-trial')
    def start_trial(self, request, pk=None):
        """
        Start the church's free trial, once.

        POST /api/v1/churches/:id/start-trial/

        Registration already starts the trial, so for a church admin this only
        reports the existing trial. A church can never restart its own trial;
        only a platform superadmin can (e.g. to give a church a fresh trial).
        """
        church = self.get_object()
        
        # Check permissions
        if not (request.user.is_superadmin or 
                (request.user.church and request.user.church.id == church.id and request.user.is_church_admin)):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if church.trial_started_at is None or request.user.is_superadmin:
            subscriptions.start_trial(church)
            church.save(update_fields=['plan', 'subscription_status',
                                       'trial_started_at', 'trial_end_date', 'updated_at'])
            message = 'Trial started successfully'
        else:
            message = 'Trial already started'

        return Response({
            'success': True,
            'message': message,
            'trial_started_at': church.trial_started_at,
            'trial_end_date': church.trial_end_date,
            'days_remaining': church.get_days_until_expiration(),
        })
    
    @action(detail=True, methods=['post'], url_path='upgrade-subscription', url_name='upgrade-subscription')
    def upgrade_subscription(self, request, pk=None):
        """
        Manually set a church's paid plan, without payment.

        Platform superadmins only (e.g. to comp a church). Church admins used to
        be allowed, which let any church give itself a paid plan for free; they
        must go through the Paystack payment flow instead.

        POST /api/v1/churches/:id/upgrade-subscription/
        Body: {
            "plan": "basic|standard|premium|enterprise",
            "duration": "monthly|yearly"
        }
        """
        from django.utils import timezone
        from datetime import timedelta

        if not request.user.is_superadmin:
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        church = self.get_object()

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
    
    @action(detail=True, methods=['get'], url_path='subscription-payments')
    def subscription_payments(self, request, pk=None):
        """
        The church's completed subscription payments, newest first (church admins
        and platform superadmins). Read-only billing history for the Billing page.

        GET /api/v1/churches/:id/subscription-payments/
        """
        church = self.get_object()
        if not (request.user.is_superadmin
                or (request.user.church_id == church.id and request.user.is_church_admin)):
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        payments = church.subscription_payments.filter(status='completed').order_by('-completed_at')
        return Response({
            'success': True,
            'payments': [{
                'reference': payment.reference,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'plan': payment.plan,
                'duration': payment.duration,
                'payment_method': payment.payment_method,
                'completed_at': payment.completed_at,
                'period_start': payment.subscription_start_date,
                'period_end': payment.subscription_end_date,
            } for payment in payments[:BILLING_HISTORY_LIMIT]],
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