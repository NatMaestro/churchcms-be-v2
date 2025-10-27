"""
Payment URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, PledgeViewSet, TaxReceiptViewSet

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment')
router.register(r'pledges', PledgeViewSet, basename='pledge')
router.register(r'tax-receipts', TaxReceiptViewSet, basename='tax-receipt')

urlpatterns = router.urls

