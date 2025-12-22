"""
Subscription payment views for Paystack integration.
"""

import os
import requests
import logging
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import uuid

from .models import Church
from .models_subscription_payment import SubscriptionPayment

logger = logging.getLogger(__name__)

# Paystack Configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')
PAYSTACK_BASE_URL = 'https://api.paystack.co'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initialize_subscription_payment(request):
    """
    Initialize a subscription payment with Paystack.
    
    POST /api/v1/churches/subscription-payment/initialize/
    Body: {
        "church_id": 1,
        "plan": "basic|standard|premium|enterprise",
        "duration": "monthly|yearly",
        "email": "user@example.com",
        "name": "User Name"
    }
    """
    if not PAYSTACK_SECRET_KEY:
        return Response({
            'success': False,
            'error': 'Paystack is not configured. Please set PAYSTACK_SECRET_KEY in environment variables.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    church_id = request.data.get('church_id')
    plan = request.data.get('plan')
    duration = request.data.get('duration', 'monthly')
    email = request.data.get('email')
    name = request.data.get('name', '')
    
    # Validation
    if not all([church_id, plan, email]):
        return Response({
            'success': False,
            'error': 'Missing required fields: church_id, plan, email'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if plan not in ['basic', 'standard', 'premium', 'enterprise']:
        return Response({
            'success': False,
            'error': 'Invalid plan. Must be: basic, standard, premium, or enterprise'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if duration not in ['monthly', 'yearly']:
        return Response({
            'success': False,
            'error': 'Invalid duration. Must be: monthly or yearly'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get church
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Church not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if not (request.user.is_superadmin or 
            (request.user.church and request.user.church.id == church.id and request.user.is_church_admin)):
        return Response({
            'success': False,
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Calculate amount based on plan and duration
    plan_prices = {
        'basic': {'monthly': 19, 'yearly': 205},  # 10% discount for yearly
        'standard': {'monthly': 29, 'yearly': 313},
        'premium': {'monthly': 79, 'yearly': 853},
        'enterprise': {'monthly': 199, 'yearly': 2149},
    }
    
    amount = plan_prices.get(plan, {}).get(duration, 0)
    if amount == 0:
        return Response({
            'success': False,
            'error': 'Invalid plan or duration combination'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert to smallest currency unit (kobo for NGN, pesewas for GHS)
    amount_in_cents = int(amount * 100)
    
    # Generate unique reference
    reference = f"SUB_{church.id}_{uuid.uuid4().hex[:12].upper()}"
    
    try:
        # Create payment record
        payment = SubscriptionPayment.objects.create(
            church=church,
            amount=amount,
            currency='GHS',
            plan=plan,
            duration=duration,
            reference=reference,
            status='pending',
            user_email=email,
            user_name=name,
        )
        
        # Initialize payment with Paystack
        paystack_url = f"{PAYSTACK_BASE_URL}/transaction/initialize"
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        # Get callback URL - Point to frontend callback page for better UX
        # The frontend page will then call the verify endpoint
        # Construct frontend URL using church's subdomain
        # Initialize variables to avoid UnboundLocalError
        callback_url = None
        scheme = 'https'
        base_domain = 'faithflow360.com'
        port = None
        
        try:
            from urllib.parse import urlparse
            
            # Get FRONTEND_URL from settings (e.g., https://faithflow360.com or http://localhost:5173)
            frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
            parsed_base = urlparse(frontend_base)
            
            # Initialize defaults from FRONTEND_URL setting
            scheme = parsed_base.scheme
            domain_parts = parsed_base.netloc.split(':')[0].split('.')
            if len(domain_parts) >= 2 and domain_parts[-2] != 'localhost':
                base_domain = '.'.join(domain_parts[-2:])
            else:
                base_domain = parsed_base.netloc.split(':')[0]
            # Extract port from netloc (format: hostname:port)
            try:
                if ':' in parsed_base.netloc:
                    port = int(parsed_base.netloc.split(':')[1])
                else:
                    port = None
            except (ValueError, IndexError):
                port = None
            
            # Try to get frontend URL from request Origin header first (most reliable)
            origin = request.META.get('HTTP_ORIGIN', '')
            referer = request.META.get('HTTP_REFERER', '')
            
            # Determine the base domain and scheme from headers if available
            # Filter out API domains - we only want frontend domains
            if origin and 'api.' not in origin.lower():
                # Extract from Origin header (e.g., https://apostolic.faithflow360.com)
                parsed = urlparse(origin)
                scheme = parsed.scheme
                # Extract base domain: apostolic.faithflow360.com -> faithflow360.com
                domain_parts = parsed.netloc.split(':')[0].split('.')  # Remove port
                if len(domain_parts) >= 2 and domain_parts[-2] != 'localhost':
                    # Production: subdomain.domain.com -> domain.com
                    base_domain = '.'.join(domain_parts[-2:])
                    port = None  # No port for production
                elif 'localhost' in parsed.netloc:
                    # Localhost: subdomain.localhost:5173 -> localhost
                    base_domain = 'localhost'
                    port = parsed.port if parsed.port else 5173
                else:
                    base_domain = parsed.netloc.split(':')[0]
                    port = parsed.port if parsed.port else None
            elif referer and 'api.' not in referer.lower():
                # Fallback to Referer header (but not API domain)
                parsed = urlparse(referer)
                scheme = parsed.scheme
                domain_parts = parsed.netloc.split(':')[0].split('.')
                if len(domain_parts) >= 2 and domain_parts[-2] != 'localhost':
                    base_domain = '.'.join(domain_parts[-2:])
                    port = None  # No port for production
                elif 'localhost' in parsed.netloc:
                    base_domain = 'localhost'
                    port = parsed.port if parsed.port else 5173
                else:
                    base_domain = parsed.netloc.split(':')[0]
                    port = parsed.port if parsed.port else None
            
            # Construct callback URL with church subdomain
            if church.subdomain:
                if 'localhost' in base_domain:
                    # Local development: http://{subdomain}.localhost:5173
                    port_str = f":{port}" if port else ":5173"
                    callback_url = f"{scheme}://{church.subdomain}.{base_domain}{port_str}/subscription/payment/callback"
                else:
                    # Production: https://{subdomain}.faithflow360.com
                    callback_url = f"{scheme}://{church.subdomain}.{base_domain}/subscription/payment/callback"
            else:
                # No subdomain, use base URL
                if 'localhost' in base_domain:
                    port_str = f":{port}" if port else ":5173"
                else:
                    port_str = ""
                callback_url = f"{scheme}://{base_domain}{port_str}/subscription/payment/callback"
            
            logger.info(f"🔗 Callback URL: {callback_url} (Church subdomain: {church.subdomain}, Origin: {origin}, Base domain: {base_domain})")
        except Exception as e:
            logger.error(f"❌ Error constructing callback URL: {str(e)}", exc_info=True)
            # Fallback to a simple callback URL
            if church.subdomain:
                callback_url = f"https://{church.subdomain}.faithflow360.com/subscription/payment/callback"
            else:
                frontend_fallback = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
                callback_url = frontend_fallback.rstrip('/') + '/subscription/payment/callback'
            logger.warning(f"⚠️ Using fallback callback URL: {callback_url}")
        
        # Ensure callback_url is set (safety check)
        if not callback_url:
            if church.subdomain:
                callback_url = f"https://{church.subdomain}.faithflow360.com/subscription/payment/callback"
            else:
                frontend_fallback = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
                callback_url = frontend_fallback.rstrip('/') + '/subscription/payment/callback'
            logger.warning(f"⚠️ Callback URL was None, using final fallback: {callback_url}")
        
        payload = {
            'email': email,
            'amount': amount_in_cents,
            'reference': reference,
            'callback_url': callback_url,
            'metadata': {
                'church_id': church.id,
                'church_name': church.name,
                'plan': plan,
                'duration': duration,
                'payment_id': payment.id,
                'user_name': name,
            },
            'channels': ['card', 'bank', 'ussd', 'qr', 'mobile_money', 'bank_transfer'],
        }
        
        logger.info(f"🔄 Initializing Paystack payment: {reference} for church {church.id}")
        
        response = requests.post(paystack_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        paystack_data = response.json()
        
        if paystack_data.get('status'):
            # Update payment record with Paystack response
            payment.paystack_reference = paystack_data.get('data', {}).get('reference', '')
            payment.authorization_url = paystack_data.get('data', {}).get('authorization_url', '')
            payment.paystack_response = paystack_data
            payment.status = 'processing'
            payment.save(update_fields=['paystack_reference', 'authorization_url', 'paystack_response', 'status', 'updated_at'])
            
            logger.info(f"✅ Paystack payment initialized: {reference}, URL: {payment.authorization_url}")
            
            return Response({
                'success': True,
                'authorization_url': payment.authorization_url,
                'reference': reference,
                'payment_id': payment.id,
            })
        else:
            payment.status = 'failed'
            payment.paystack_response = paystack_data
            payment.save(update_fields=['status', 'paystack_response', 'updated_at'])
            
            logger.error(f"❌ Paystack initialization failed: {paystack_data}")
            
            return Response({
                'success': False,
                'error': paystack_data.get('message', 'Failed to initialize payment')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except requests.RequestException as e:
        logger.error(f"❌ Paystack API error: {str(e)}")
        if 'payment' in locals():
            payment.status = 'failed'
            payment.save(update_fields=['status', 'updated_at'])
        
        return Response({
            'success': False,
            'error': f'Payment gateway error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"❌ Unexpected error initializing payment: {str(e)}")
        return Response({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # AllowAny because Paystack redirects here
def verify_subscription_payment(request):
    """
    Verify a subscription payment after Paystack redirect.
    
    GET /api/v1/churches/subscription-payment/verify/?reference=SUB_123_ABC
    """
    reference = request.query_params.get('reference')
    
    if not reference:
        return Response({
            'success': False,
            'error': 'Reference is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        payment = SubscriptionPayment.objects.get(reference=reference)
    except SubscriptionPayment.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Payment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # If already verified and activated, return success
    if payment.status == 'completed' and payment.subscription_activated:
        return Response({
            'success': True,
            'message': 'Payment already verified',
            'payment': {
                'id': payment.id,
                'plan': payment.plan,
                'amount': str(payment.amount),
                'status': payment.status,
            }
        })
    
    # Verify with Paystack
    if not payment.paystack_reference:
        return Response({
            'success': False,
            'error': 'Payment reference not found'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verify_url = f"{PAYSTACK_BASE_URL}/transaction/verify/{payment.paystack_reference}"
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
        }
        
        response = requests.get(verify_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        paystack_data = response.json()
        
        if paystack_data.get('status') and paystack_data.get('data', {}).get('status') == 'success':
            # Payment successful
            with transaction.atomic():
                payment.status = 'completed'
                payment.paystack_response = paystack_data
                payment.mark_completed()
                
                # Activate subscription
                payment.activate_subscription()
                
                logger.info(f"✅ Payment verified and subscription activated: {reference}")
            
            return Response({
                'success': True,
                'message': 'Payment verified successfully',
                'payment': {
                    'id': payment.id,
                    'plan': payment.plan,
                    'duration': payment.duration,
                    'amount': str(payment.amount),
                    'status': payment.status,
                    'subscription_activated': payment.subscription_activated,
                }
            })
        else:
            # Payment failed
            payment.status = 'failed'
            payment.paystack_response = paystack_data
            payment.save(update_fields=['status', 'paystack_response', 'updated_at'])
            
            logger.warning(f"⚠️ Payment verification failed: {reference}")
            
            return Response({
                'success': False,
                'error': 'Payment verification failed',
                'payment': {
                    'id': payment.id,
                    'status': payment.status,
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except requests.RequestException as e:
        logger.error(f"❌ Paystack verification error: {str(e)}")
        return Response({
            'success': False,
            'error': f'Payment verification error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"❌ Unexpected error verifying payment: {str(e)}")
        return Response({
            'success': False,
            'error': 'An unexpected error occurred during verification'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Webhooks don't use authentication
def paystack_webhook(request):
    """
    Handle Paystack webhook events.
    
    POST /api/v1/churches/subscription-payment/webhook/
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Verify webhook signature (optional but recommended)
    # You can add Paystack signature verification here
    
    try:
        payload = json.loads(request.body)
        event = payload.get('event')
        data = payload.get('data', {})
        
        logger.info(f"📥 Paystack webhook received: {event}")
        
        if event == 'charge.success':
            reference = data.get('reference')
            
            if not reference:
                return JsonResponse({'error': 'Reference not found'}, status=400)
            
            try:
                payment = SubscriptionPayment.objects.get(paystack_reference=reference)
            except SubscriptionPayment.DoesNotExist:
                logger.warning(f"⚠️ Payment not found for webhook reference: {reference}")
                return JsonResponse({'error': 'Payment not found'}, status=404)
            
            # Only process if not already completed
            if payment.status != 'completed':
                with transaction.atomic():
                    payment.status = 'completed'
                    payment.paystack_response = payload
                    payment.mark_completed()
                    
                    # Activate subscription
                    payment.activate_subscription()
                    
                    logger.info(f"✅ Webhook: Payment completed and subscription activated: {reference}")
            
            return JsonResponse({'status': 'success'})
        
        elif event == 'charge.failed':
            reference = data.get('reference')
            
            if reference:
                try:
                    payment = SubscriptionPayment.objects.get(paystack_reference=reference)
                    payment.status = 'failed'
                    payment.paystack_response = payload
                    payment.save(update_fields=['status', 'paystack_response', 'updated_at'])
                    
                    logger.warning(f"⚠️ Webhook: Payment failed: {reference}")
                except SubscriptionPayment.DoesNotExist:
                    pass
            
            return JsonResponse({'status': 'received'})
        
        else:
            # Acknowledge other events
            return JsonResponse({'status': 'received'})
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

