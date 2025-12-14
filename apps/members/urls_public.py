"""
Public member request URLs (no authentication required).
"""

from django.urls import path
from .views_member_requests import submit_member_request

urlpatterns = [
    path('submit/', submit_member_request, name='submit-member-request-public'),
]

