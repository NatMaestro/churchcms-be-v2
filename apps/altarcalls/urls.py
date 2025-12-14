"""
Altar call URLs.
"""

from rest_framework.routers import DefaultRouter
from .views import AltarCallViewSet

router = DefaultRouter()
router.register(r'', AltarCallViewSet, basename='altar-call')

urlpatterns = router.urls






