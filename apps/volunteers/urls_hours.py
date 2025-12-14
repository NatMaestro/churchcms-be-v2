"""
Volunteer hours URLs.
"""

from rest_framework.routers import DefaultRouter
from .views import VolunteerHoursViewSet

router = DefaultRouter()
router.register(r'', VolunteerHoursViewSet, basename='volunteer-hours')

urlpatterns = router.urls






