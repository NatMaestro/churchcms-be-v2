"""
One-time password tokens, shared by password reset and new-member invites.

Only a SHA-256 hash of each token is stored, so a leaked database (or the
Django admin) can't be used to reset anyone's password. The raw token exists
only in the emailed link. A plain hash is enough: the token is 32 random bytes,
so there is nothing to guess.
"""
import hashlib
import secrets

from django.utils import timezone

from .models import PasswordResetToken

PASSWORD_TOKEN_BYTES = 32


def hash_password_token(token):
    """What is stored for (and looked up by) a raw token from a link."""
    return hashlib.sha256(token.encode()).hexdigest()


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
        token=hash_password_token(token),
        email=user.email,
        expires_at=timezone.now() + lifetime,
    )
    return token  # the raw token, for the emailed link only
