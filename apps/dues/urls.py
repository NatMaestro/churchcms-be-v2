"""
Dues URLs (mounted at /api/v1/dues/).
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DuesAssignmentViewSet, DuesCategoryViewSet, DuesPaymentViewSet, DuesPlanViewSet, member_card

router = DefaultRouter()
router.register(r'plans', DuesPlanViewSet, basename='dues-plan')
router.register(r'categories', DuesCategoryViewSet, basename='dues-category')
router.register(r'assignments', DuesAssignmentViewSet, basename='dues-assignment')
router.register(r'payments', DuesPaymentViewSet, basename='dues-payment')

urlpatterns = [
    path('my-card/', member_card, name='dues-my-card'),
    path('member-card/', member_card, name='dues-member-card'),
] + router.urls
