"""
Authentication views.
"""

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.conf import settings
from django.middleware.csrf import get_token
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChurchRegistrationSerializer
)
from .models import PasswordResetToken
from apps.churches.models import Church, Domain
from django.utils import timezone
from datetime import timedelta
import secrets

User = get_user_model()


def set_auth_cookies(response, access_token: str, refresh_token: str, request):
    """
    Attach HttpOnly cookies for access and refresh tokens.
    """
    secure_flag = not settings.DEBUG
    cookie_domain = settings.COOKIE_DOMAIN or None
    # Access token cookie
    response.set_cookie(
        settings.ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        httponly=True,
        secure=secure_flag,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        domain=cookie_domain,
        path='/',
        max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
    )
    # Refresh token cookie
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=secure_flag,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        domain=cookie_domain,
        path='/',
        max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
    )
    # Ensure a CSRF token is issued alongside auth cookies
    csrf_token = get_token(request)
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_token,
        secure=secure_flag,
        samesite=settings.CSRF_COOKIE_SAMESITE,
        domain=cookie_domain,
        path='/',
    )


def clear_auth_cookies(response):
    """
    Remove auth cookies from the browser.
    """
    cookie_domain = settings.COOKIE_DOMAIN or None
    for name in [settings.ACCESS_TOKEN_COOKIE_NAME, settings.REFRESH_TOKEN_COOKIE_NAME]:
        response.set_cookie(
            name,
            '',
            max_age=0,
            secure=not settings.DEBUG,
            httponly=True,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            domain=cookie_domain,
            path='/',
        )
    # Clear CSRF cookie
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        '',
        max_age=0,
        secure=not settings.DEBUG,
        samesite=settings.CSRF_COOKIE_SAMESITE,
        domain=cookie_domain,
        path='/',
    )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with user data."""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """
        Issue JWTs and also set HttpOnly cookies for browser clients.
        """
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK and response.data.get('access') and response.data.get('refresh'):
            set_auth_cookies(response, response.data['access'], response.data['refresh'], request)
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh access token using the refresh token from cookie (preferred) or request data.
    """

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        # If refresh token not supplied in body, pull from cookie
        if 'refresh' not in data:
            refresh_from_cookie = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
            if refresh_from_cookie:
                data['refresh'] = refresh_from_cookie

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)

        if response.status_code == status.HTTP_200_OK and response.data.get('access'):
            # When rotation is enabled, refresh may also be returned
            access_token = response.data['access']
            refresh_token = response.data.get('refresh') or request.data.get('refresh')
            if refresh_token:
                set_auth_cookies(response, access_token, refresh_token, request)
        return response


class RegisterView(APIView):
    """User registration view."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Check if this is a church registration (has church_name and subdomain)
        if 'church_name' in request.data and 'subdomain' in request.data:
            # Use church registration flow
            serializer = ChurchRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                # Use transaction to ensure atomicity - if user creation fails, rollback church
                try:
                    validated_data = serializer.validated_data
                    
                    # Start transaction in public schema
                    import logging
                    logger = logging.getLogger(__name__)
                    
                    logger.info(f"🏗️  Starting church registration for: {validated_data['church_name']}")
                    logger.info(f"   Subdomain: {validated_data['subdomain']}")
                    logger.info(f"   Admin: {validated_data['name']} ({validated_data['email']})")
                    
                    with transaction.atomic():
                        # Step 1: Create church (in public schema)
                        logger.info("📋 Step 1/4: Creating church record...")
                        church = Church.objects.create(
                            schema_name=validated_data['subdomain'],
                            name=validated_data['church_name'],
                            subdomain=validated_data['subdomain'],
                            email=validated_data['email'],
                            denomination=validated_data.get('denomination', ''),
                            features=validated_data.get('features', {}),
                            plan='trial',
                            is_active=True
                        )
                        logger.info(f"   ✅ Church created: {church.name} (ID: {church.id})")
                        
                        # Log enabled features
                        features = validated_data.get('features', {})
                        if features:
                            enabled_features = [name for name, enabled in features.items() if enabled]
                            disabled_features = [name for name, enabled in features.items() if not enabled]
                            
                            if enabled_features:
                                logger.info(f"   🎯 Enabled features ({len(enabled_features)}):")
                                for feature in enabled_features:
                                    logger.info(f"      ✅ {feature}")
                            
                            if disabled_features:
                                logger.info(f"   ⚪ Disabled features ({len(disabled_features)}):")
                                for feature in disabled_features[:5]:  # Show first 5
                                    logger.info(f"      ⭕ {feature}")
                                if len(disabled_features) > 5:
                                    logger.info(f"      ... and {len(disabled_features) - 5} more")
                        else:
                            logger.info("   🎯 Using default features (no custom configuration)")
                        
                        # Step 2: Create domains
                        logger.info("🌐 Step 2/4: Setting up domains...")
                        Domain.objects.create(
                            domain=f"{validated_data['subdomain']}.localhost",
                            tenant=church,
                            is_primary=True
                        )
                        logger.info(f"   ✅ Created domain: {validated_data['subdomain']}.localhost")
                        
                        # Create domain for production (if not in debug)
                        if not settings.DEBUG:
                            Domain.objects.create(
                                domain=f"{validated_data['subdomain']}.faithflow360.com",
                                tenant=church,
                                is_primary=False
                            )
                            logger.info(f"   ✅ Created domain: {validated_data['subdomain']}.faithflow360.com")
                        
                        # Step 3: Switch to tenant schema and create user
                        logger.info("👤 Step 3/4: Creating tenant schema and admin user...")
                        connection.set_tenant(church)
                        logger.info(f"   ✅ Switched to tenant schema: {church.schema_name}")
                        
                        try:
                            # Create admin user in tenant schema
                            admin_user = User.objects.create_user(
                                email=validated_data['email'],
                                password=validated_data['password'],
                                name=validated_data['name'],
                                church=church,
                                role='admin',
                                is_active=True,
                                is_staff=True
                            )
                            logger.info(f"   ✅ Admin user created: {admin_user.email} (ID: {admin_user.id})")
                            
                            # Step 4: Generate JWT tokens
                            logger.info("🔑 Step 4/4: Generating authentication tokens...")
                            refresh = RefreshToken.for_user(admin_user)
                            logger.info("   ✅ Tokens generated successfully")
                            
                            logger.info(f"🎉 Church registration completed successfully for: {church.name}")
                            
                            # Switch back to public schema for response
                            connection.set_schema_to_public()
                            
                            response = Response({
                                'success': True,
                                'message': 'Church and admin user created successfully',
                                'user': UserSerializer(admin_user).data,
                                'church': {
                                    'id': church.id,
                                    'name': church.name,
                                    'subdomain': church.subdomain,
                                    'schema_name': church.schema_name,
                                },
                                'access': str(refresh.access_token),
                                'refresh': str(refresh),
                            }, status=status.HTTP_201_CREATED)
                            
                            # Attach auth cookies to response
                            set_auth_cookies(response, str(refresh.access_token), str(refresh), request)
                            return response
                            
                        except Exception as user_error:
                            # If user creation fails, rollback the church creation
                            connection.set_schema_to_public()
                            # Delete the church and domains we just created
                            Domain.objects.filter(tenant=church).delete()
                            church.delete()
                            raise user_error
                    
                except Exception as e:
                    # Switch back to public schema on error
                    connection.set_schema_to_public()
                    import traceback
                    error_detail = str(e)
                    # Check if it's a unique constraint violation
                    if 'unique constraint' in error_detail.lower() or 'already exists' in error_detail.lower():
                        if 'email' in error_detail.lower():
                            error_detail = 'A user with this email already exists in this church.'
                        elif 'subdomain' in error_detail.lower():
                            error_detail = 'This subdomain is already taken.'
                    
                    return Response({
                        'success': False,
                        'errors': {'detail': error_detail}
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Regular user registration (no church)
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            
            response = Response({
                'success': True,
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)

            set_auth_cookies(response, str(refresh.access_token), str(refresh), request)
            return response
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Logout view - blacklist refresh token."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh') or request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
            token = RefreshToken(refresh_token)
            token.blacklist()

            response = Response({
                'success': True,
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)
            clear_auth_cookies(response)
            return response
        except Exception:
            return Response({
                'success': False,
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    """Get current user profile."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'user': serializer.data
        })


class ChangePasswordView(APIView):
    """Change password view."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            
            # Verify current password
            if not user.check_password(serializer.validated_data['current_password']):
                return Response({
                    'success': False,
                    'error': 'Current password is incorrect'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.must_change_password = False
            user.last_password_change = timezone.now()
            user.save()
            
            return Response({
                'success': True,
                'message': 'Password changed successfully'
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    """Forgot password view - send reset token."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email)
                
                # Generate reset token
                token = f"reset_{int(timezone.now().timestamp())}_{secrets.token_urlsafe(16)}"
                
                # Create reset token record
                reset_token = PasswordResetToken.objects.create(
                    user=user,
                    token=token,
                    email=email,
                    expires_at=timezone.now() + timedelta(hours=24)
                )
                
                # TODO: Send email with reset link
                # send_password_reset_email(user, token)
                
                return Response({
                    'success': True,
                    'message': 'Password reset email sent',
                    'token': token  # Remove in production
                })
            except User.DoesNotExist:
                # Don't reveal if user exists
                return Response({
                    'success': True,
                    'message': 'If the email exists, a reset link has been sent'
                })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    """Reset password with token."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            try:
                reset_token = PasswordResetToken.objects.get(token=token)
                
                if not reset_token.is_valid():
                    return Response({
                        'success': False,
                        'error': 'Token is invalid or expired'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Reset password
                user = reset_token.user
                user.set_password(new_password)
                user.save()
                
                # Mark token as used
                reset_token.used = True
                reset_token.save()
                
                return Response({
                    'success': True,
                    'message': 'Password reset successfully'
                })
            except PasswordResetToken.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Invalid token'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """User management viewset."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter users by church (except superadmins)."""
        user = self.request.user
        if user.is_superadmin:
            return User.objects.all()
        return User.objects.filter(church=user.church)
    
    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def create(self, request, *args, **kwargs):
        """Create user with proper church assignment."""
        # In multi-tenant setup, users created in a tenant schema MUST belong to that tenant's church
        # This prevents data inconsistency where a user exists in tenant A's schema
        # but their church field points to tenant B
        
        # Always force the church to be the current tenant's church
        # This ensures data consistency regardless of what the frontend sends
        if request.user.church:
            request.data['church'] = request.user.church.id
        
        return super().create(request, *args, **kwargs)
