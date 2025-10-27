"""
Analytics and dashboard URLs.
"""

from django.urls import path
from .views import DashboardView, AnalyticsView

urlpatterns = [
    path('stats/', DashboardView.as_view(), name='dashboard-stats'),
    path('overview/', AnalyticsView.as_view(), name='analytics-overview'),
]

