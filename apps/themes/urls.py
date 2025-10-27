"""
Theme URLs.
"""

from rest_framework.routers import DefaultRouter
from .views import ThemeViewSet

router = DefaultRouter()
router.register(r'', ThemeViewSet, basename='theme')

urlpatterns = router.urls

