"""
Subscription and trial management middleware.
Checks subscription status and blocks access when expired.
"""

from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class SubscriptionMiddleware:
    """
    Middleware to check subscription/trial status and block access when expired.
    
    Features:
    - Checks trial expiration
    - Checks subscription expiration
    - Allows grace period (configurable days)
    - Blocks access after grace period
    - Returns appropriate error messages
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Public routes that don't require subscription check
        public_paths = [
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/auth/refresh/',
            '/api/v1/auth/forgot-password/',
            '/api/v1/auth/reset-password/',
            '/api/v1/churches/subscription-payment/webhook/',  # Paystack webhook (no tenant needed)
            '/health/',
            '/api/docs/',
            '/api/schema/',
        ]
        
        is_public_route = any(request.path.startswith(path) for path in public_paths)
        
        # Skip subscription check for public routes
        if is_public_route:
            return self.get_response(request)
        
        # Get current tenant (church)
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            # No tenant means this is a public route or tenant not set yet
            return self.get_response(request)
        
        # Bypass subscription check if flag is set (for testing or special cases)
        if getattr(tenant, 'bypass_subscription_check', False):
            logger.info(f'Subscription check bypassed for church: {tenant.name} (ID: {tenant.id})')
            # Still add subscription info but mark as bypassed
            request.subscription_status = {
                'status': 'bypassed',
                'can_access': True,
                'error': None,
                'days_remaining': None,
                'bypassed': True,
            }
            return self.get_response(request)
        
        # Bypass for apostolic church (testing/development)
        if hasattr(tenant, 'subdomain') and tenant.subdomain in ['apostolic', 'apostolicchurch']:
            logger.info(f'Subscription check bypassed for apostolic church: {tenant.name}')
            request.subscription_status = {
                'status': 'bypassed',
                'can_access': True,
                'error': None,
                'days_remaining': None,
                'bypassed': True,
            }
            return self.get_response(request)
        
        # Check subscription status
        subscription_status = self._check_subscription_status(tenant)
        
        if not subscription_status['can_access']:
            return JsonResponse(
                {
                    'error': subscription_status['error'],
                    'status': subscription_status['status'],
                    'expired': True,
                    'upgrade_required': True,
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add subscription info to request for use in views
        request.subscription_status = subscription_status
        
        return self.get_response(request)
    
    def _check_subscription_status(self, church):
        """
        Check subscription/trial status for a church.
        Returns dict with status, can_access, and error message if applicable.
        """
        now = timezone.now()
        grace_period_days = getattr(church, 'grace_period_days', 7)
        
        # Check if cancelled or suspended
        if church.subscription_status in ['cancelled', 'suspended']:
            return {
                'status': church.subscription_status,
                'can_access': False,
                'error': f'Your account is {church.subscription_status}. Please contact support.',
                'days_remaining': None,
            }
        
        # Check trial expiration
        if church.plan == 'trial' and church.trial_end_date:
            grace_period_end = church.trial_end_date + timedelta(days=grace_period_days)
            
            if now > grace_period_end:
                return {
                    'status': 'trial_expired',
                    'can_access': False,
                    'error': 'Your free trial has expired. Please upgrade to continue using FaithFlows.',
                    'days_remaining': 0,
                }
            
            if now > church.trial_end_date:
                days_in_grace = (grace_period_end - now).days
                return {
                    'status': 'trial_expiring',
                    'can_access': True,  # Allow access during grace period
                    'error': None,
                    'days_remaining': days_in_grace,
                    'warning': f'Your trial has expired. You have {days_in_grace} days to upgrade.',
                }
        
        # Check subscription expiration
        if church.subscription_end_date:
            grace_period_end = church.subscription_end_date + timedelta(days=grace_period_days)
            
            if now > grace_period_end:
                return {
                    'status': 'subscription_expired',
                    'can_access': False,
                    'error': 'Your subscription has expired. Please renew to continue using FaithFlows.',
                    'days_remaining': 0,
                }
            
            if now > church.subscription_end_date:
                days_in_grace = (grace_period_end - now).days
                return {
                    'status': 'subscription_expiring',
                    'can_access': True,  # Allow access during grace period
                    'error': None,
                    'days_remaining': days_in_grace,
                    'warning': f'Your subscription has expired. You have {days_in_grace} days to renew.',
                }
        
        # Active subscription
        days_remaining = None
        if church.plan == 'trial' and church.trial_end_date:
            days_remaining = (church.trial_end_date - now).days
        elif church.subscription_end_date:
            days_remaining = (church.subscription_end_date - now).days
        
        return {
            'status': 'active',
            'can_access': True,
            'error': None,
            'days_remaining': max(0, days_remaining) if days_remaining is not None else None,
        }

