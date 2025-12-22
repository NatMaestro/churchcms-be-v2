"""
Church URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChurchViewSet
from .views_payment import (
    initialize_subscription_payment,
    verify_subscription_payment,
    paystack_webhook,
)

router = DefaultRouter()
router.register(r'', ChurchViewSet, basename='church')

urlpatterns = [
    path('', include(router.urls)),
    # Subscription payment endpoints
    path('subscription-payment/initialize/', initialize_subscription_payment, name='initialize-subscription-payment'),
    path('subscription-payment/verify/', verify_subscription_payment, name='verify-subscription-payment'),
    path('subscription-payment/callback/', verify_subscription_payment, name='payment-callback'),
    path('subscription-payment/webhook/', paystack_webhook, name='paystack-webhook'),
]






