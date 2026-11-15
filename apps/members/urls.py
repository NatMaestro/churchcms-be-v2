"""
Member URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MemberViewSet
from .views_member_requests import MemberRequestViewSet, submit_member_request

router = DefaultRouter()
# 'requests' must come first: the member routes match any single path segment
# as a member id, so 'requests/' would otherwise be looked up as a member.
router.register(r'requests', MemberRequestViewSet, basename='member-request')
router.register(r'', MemberViewSet, basename='member')

urlpatterns = [
    path('member-requests/submit/', submit_member_request, name='submit-member-request'),
    path('', include(router.urls)),
]






