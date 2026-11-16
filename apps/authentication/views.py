"""
Authentication views.
"""

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
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
from .tokens import issue_password_token
from apps.churches.models import Church, Domain
from apps.churches.subscriptions import start_trial
from core.frontend_links import frontend_url
from core.permissions import IsChurchAdminOrSuperAdmin
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

PASSWORD_RESET_TOKEN_LIFETIME_HOURS = 1
PASSWORD_RESET_TOKEN_LIFETIME = timedelta(hours=PASSWORD_RESET_TOKEN_LIFETIME_HOURS)
FORGOT_PASSWORD_RESPONSE_MESSAGE = 'If an account exists for that email, a reset link has been sent.'


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
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # Same handling as simplejwt's own TokenViewBase: an expired or
            # revoked refresh token is a 401, not a 500.
            raise InvalidToken(e.args[0])
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
                            is_active=True
                        )
                        # The free trial starts now, on the server; the client cannot extend it.
                        start_trial(church)
                        church.save(update_fields=['plan', 'subscription_status',
                                                   'trial_started_at', 'trial_end_date'])
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
        refresh_token = request.data.get('refresh') or request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        try:
            if not refresh_token:
                # RefreshToken(None) would mint a brand-new token, not fail.
                raise TokenError('No refresh token supplied')
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            # Missing, expired or already-blacklisted refresh token: nothing left
            # to revoke, but the browser must still be logged out below.
            logger.info('logout_without_valid_refresh_token', extra={'user_id': request.user.pk})

        response = Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response


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

            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user is not None:
                self._issue_reset_token(user)

            # Identical response whether or not the account exists, so this
            # endpoint cannot be used to discover registered emails. The token
            # is only ever delivered by email, never in the response.
            return Response({
                'success': True,
                'message': FORGOT_PASSWORD_RESPONSE_MESSAGE,
            })

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _issue_reset_token(user):
        """Create a fresh reset token for `user` and email them the reset link."""
        token = issue_password_token(user, PASSWORD_RESET_TOKEN_LIFETIME)

        # Opens on the user's church site; platform admins get the main site.
        reset_link = frontend_url(f'/reset-password?token={token}', user.church)
        try:
            send_mail(
                subject='Reset your FaithFlow password',
                message=(
                    f"Hello {user.name},\n\n"
                    "We received a request to reset your FaithFlow password. "
                    f"Use this link within {PASSWORD_RESET_TOKEN_LIFETIME_HOURS} hour(s):\n\n"
                    f"{reset_link}\n\n"
                    "If you did not ask for this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        except Exception:
            # The response stays generic either way; the failure is logged
            # (user id only, never the token) so it can be investigated.
            logger.exception('password_reset_email_failed', extra={'user_id': user.id})


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
                # They just chose this password themselves (reset or invite
                # link), so there is nothing left to force them to change.
                user.must_change_password = False
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
    """
    User management.

    - Church admins manage the users of their own church.
    - Superadmins manage everyone.
    - Members may only read their own record (the frontend loads it after login);
      every write is admin-only.
    The church a user belongs to is always set server-side, never from the request.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsChurchAdminOrSuperAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superadmin:
            return User.objects.all()
        if user.is_church_admin and user.church_id:
            return User.objects.filter(church_id=user.church_id)
        return User.objects.filter(pk=user.pk)

    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
