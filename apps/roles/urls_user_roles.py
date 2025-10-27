"""
User role URLs.
"""

from rest_framework.routers import DefaultRouter
from .views import UserRoleViewSet

router = DefaultRouter()
router.register(r'', UserRoleViewSet, basename='user-role')

urlpatterns = router.urls

