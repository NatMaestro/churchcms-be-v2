"""
Payment URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, PledgeViewSet, TaxReceiptViewSet

router = DefaultRouter()
# Named prefixes first: the payment detail route ('<pk>/') would otherwise catch them.
router.register(r'pledges', PledgeViewSet, basename='pledge')
router.register(r'tax-receipts', TaxReceiptViewSet, basename='tax-receipt')
router.register(r'', PaymentViewSet, basename='payment')

urlpatterns = router.urls






