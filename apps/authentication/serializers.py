"""
Authentication serializers.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class ChurchBasicSerializer(serializers.Serializer):
    """Basic church info for user serializer."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    subdomain = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    plan = serializers.CharField(read_only=True)


class UserSerializer(serializers.ModelSerializer):
    """User serializer."""
    
    church_name = serializers.CharField(source='church.name', read_only=True, allow_null=True)
    church_details = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'role', 'church', 'church_name', 'church_details',
            'is_active', 'must_change_password', 'created_at',
            'last_login'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_church_details(self, obj):
        """Get church details if exists."""
        if obj.church:
            return ChurchBasicSerializer(obj.church).data
        return None


class RegisterSerializer(serializers.ModelSerializer):
    """User registration serializer."""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'password_confirm']
    
    def validate(self, attrs):
        """Validate password match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Passwords do not match.'
            })
        return attrs
    
    def create(self, validated_data):
        """Create user."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data."""
    
    def validate(self, attrs):
        """Add user data to token response."""
        data = super().validate(attrs)
        
        # Add user data
        data['user'] = UserSerializer(self.user).data
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer."""
    
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    
    def validate_new_password(self, value):
        """Validate password strength."""
        # Add password strength validation here
        if len(value) < 8:
            raise serializers.ValidationError(
                'Password must be at least 8 characters long.'
            )
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    """Forgot password serializer."""
    
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Reset password serializer."""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)


class ChurchRegistrationSerializer(serializers.Serializer):
    """Church registration serializer."""
    
    # Admin user fields
    name = serializers.CharField(required=True, max_length=255)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, min_length=8, write_only=True)
    password_confirm = serializers.CharField(required=True, write_only=True)
    
    # Church fields
    church_name = serializers.CharField(required=True, max_length=255)
    subdomain = serializers.CharField(required=True, max_length=100)
    denomination = serializers.CharField(required=False, allow_blank=True, default='')
    features = serializers.JSONField(required=False, default=dict)
    
    def validate(self, attrs):
        """Validate password match and subdomain."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Passwords do not match.'
            })
        
        # Validate subdomain format
        subdomain = attrs['subdomain'].lower()
        if not subdomain.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError({
                'subdomain': 'Subdomain can only contain letters, numbers, hyphens, and underscores.'
            })
        
        # Check if subdomain already exists (in public schema)
        from apps.churches.models import Church
        if Church.objects.filter(subdomain=subdomain).exists():
            raise serializers.ValidationError({
                'subdomain': 'This subdomain is already taken.'
            })
        
        # Note: We don't check email uniqueness here because:
        # 1. Emails can be the same across different tenants (churches)
        # 2. The user will be created in the tenant schema, not public schema
        # 3. Email uniqueness is enforced per tenant schema
        
        return attrs

