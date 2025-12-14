"""
Volunteer opportunity URLs.
"""

from rest_framework.routers import DefaultRouter
from .views import VolunteerOpportunityViewSet

router = DefaultRouter()
router.register(r'', VolunteerOpportunityViewSet, basename='volunteer-opportunity')

urlpatterns = router.urls






