"""
One-time password tokens, shared by password reset and new-member invites.
"""
import secrets

from django.utils import timezone

from .models import PasswordResetToken

PASSWORD_TOKEN_BYTES = 32


def issue_password_token(user, lifetime):
    """
    Create a single-use token that lets `user` set a new password within
    `lifetime` (a timedelta). Any earlier unused token for the user stops
    working, so only the newest link is valid.
    """
    PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

    token = secrets.token_urlsafe(PASSWORD_TOKEN_BYTES)
    PasswordResetToken.objects.create(
        user=user,
        token=token,
        email=user.email,
        expires_at=timezone.now() + lifetime,
    )
    return token
