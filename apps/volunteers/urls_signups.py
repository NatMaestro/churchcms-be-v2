"""
Volunteer signup URLs.
"""

from rest_framework.routers import DefaultRouter
from .views import VolunteerSignupViewSet

router = DefaultRouter()
router.register(r'', VolunteerSignupViewSet, basename='volunteer-signup')

urlpatterns = router.urls






