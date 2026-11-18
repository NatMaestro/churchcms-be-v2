"""
Creating a church: its record and schema, its domains, its first admin and its trial.

Used when a platform admin sets a church up after a demo. Self-service
registration (RegisterView) shares the domain setup.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import connection, transaction

from apps.authentication.tokens import issue_password_token
from core.frontend_links import frontend_url

from .setup_rules import normalize_subdomain, subdomain_problem
from .subscriptions import start_trial

logger = logging.getLogger(__name__)

LOCAL_BASE_DOMAIN = 'localhost'
ADMIN_INVITE_LIFETIME_HOURS = 72


class ProvisioningError(ValueError):
    """The church cannot be created as asked (shown to the admin as-is)."""


def clean_subdomain(value):
    """The same address rules as self-service sign-up (setup_rules)."""
    subdomain = normalize_subdomain(value)
    problem = subdomain_problem(subdomain)
    if problem:
        raise ProvisioningError(problem)
    return subdomain


def create_church_domains(church):
    """The domain records every church gets (local always, production when not in DEBUG)."""
    from .models import Domain

    Domain.objects.create(domain=f'{church.subdomain}.{LOCAL_BASE_DOMAIN}', tenant=church, is_primary=True)
    if not settings.DEBUG:
        Domain.objects.create(domain=f'{church.subdomain}.{settings.PLATFORM_DOMAIN}', tenant=church,
                              is_primary=False)


def create_church_with_admin(*, church_name, subdomain, admin_name, admin_email, denomination=''):
    """
    Create a church on a fresh trial with one admin who has no password yet.
    Returns (church, admin). Call send_church_admin_invite afterwards.
    """
    from .models import Church

    User = get_user_model()
    subdomain = clean_subdomain(subdomain)
    admin_email = (admin_email or '').strip().lower()
    if Church.objects.filter(subdomain=subdomain).exists() or Church.objects.filter(schema_name=subdomain).exists():
        raise ProvisioningError('That address is already taken.')
    if User.objects.filter(email__iexact=admin_email).exists():
        raise ProvisioningError('An account with this email already exists. Use another email.')

    try:
        with transaction.atomic():
            church = Church(schema_name=subdomain, subdomain=subdomain, name=church_name.strip(),
                            email=admin_email, denomination=denomination or '', is_active=True)
            church.features = church.get_default_features()
            start_trial(church)
            church.save()  # also creates the church's schema
            create_church_domains(church)
            admin = User.objects.create_user(email=admin_email, password=None, name=admin_name.strip(),
                                             church=church, role='admin', is_active=True)
    finally:
        connection.set_schema_to_public()
    logger.info('church_provisioned', extra={'church_id': church.pk, 'admin_id': admin.pk})
    return church, admin


def send_church_admin_invite(admin, church):
    """Email the church admin a link to set their password. Returns True if handed to the mail server."""
    from datetime import timedelta

    token = issue_password_token(admin, timedelta(hours=ADMIN_INVITE_LIFETIME_HOURS))
    link = frontend_url(f'/reset-password?token={token}&invite=1', church)
    try:
        send_mail(
            subject=f'{church.name} is ready on {settings.PLATFORM_NAME}',
            message=(
                f"Hello {admin.name},\n\n"
                f"Your church, {church.name}, is set up on {settings.PLATFORM_NAME} and your free trial has started.\n\n"
                "Set your password to sign in as the church administrator. "
                f"This link works once and expires in {ADMIN_INVITE_LIFETIME_HOURS} hours:\n\n"
                f"{link}\n\n"
                "If the link has expired, reply to this email and we will send a new one."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin.email],
        )
    except Exception:
        logger.exception('church_admin_invite_failed', extra={'church_id': church.pk, 'admin_id': admin.pk})
        return False
    return True
