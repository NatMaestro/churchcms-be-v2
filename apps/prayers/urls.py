"""
Prayer request URLs.
"""

from rest_framework.routers import DefaultRouter
from .views import PrayerRequestViewSet

router = DefaultRouter()
router.register(r'', PrayerRequestViewSet, basename='prayer-request')

urlpatterns = router.urls

