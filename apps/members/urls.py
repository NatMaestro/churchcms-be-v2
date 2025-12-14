"""
Member URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MemberViewSet
from .views_member_requests import MemberRequestViewSet, submit_member_request

router = DefaultRouter()
router.register(r'', MemberViewSet, basename='member')
router.register(r'requests', MemberRequestViewSet, basename='member-request')

urlpatterns = [
    path('member-requests/submit/', submit_member_request, name='submit-member-request'),
    path('', include(router.urls)),
]






