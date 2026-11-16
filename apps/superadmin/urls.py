"""
Platform admin URLs, mounted at /api/v1/platform/ (platform superadmins only).
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (PlatformChurchViewSet, PlatformDemoRequestViewSet, PlatformOverviewView,
                    PlatformPaymentViewSet, PlatformPlanViewSet)

router = DefaultRouter()
router.register(r'churches', PlatformChurchViewSet, basename='platform-church')
router.register(r'plans', PlatformPlanViewSet, basename='platform-plan')
router.register(r'payments', PlatformPaymentViewSet, basename='platform-payment')
router.register(r'demo-requests', PlatformDemoRequestViewSet, basename='platform-demo-request')

urlpatterns = [
    path('overview/', PlatformOverviewView.as_view(), name='platform-overview'),
    path('', include(router.urls)),
]
