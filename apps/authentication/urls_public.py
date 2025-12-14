"""
Authentication URLs (public schema).
For church registration and super admin login.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomTokenObtainPairView, RegisterView

urlpatterns = [
    # Super admin login
    path('login/', CustomTokenObtainPairView.as_view(), name='superadmin_login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Church registration (public endpoint - accessible from any domain)
    path('register/', RegisterView.as_view(), name='register'),
]






