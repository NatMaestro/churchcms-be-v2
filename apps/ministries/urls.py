"""
Ministry URLs.
"""

from rest_framework.routers import DefaultRouter
from .views import MinistryViewSet

router = DefaultRouter()
router.register(r'', MinistryViewSet, basename='ministry')

urlpatterns = router.urls






