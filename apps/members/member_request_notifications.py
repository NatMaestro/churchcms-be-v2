"""
Messages sent around a membership application:
- church admins are emailed when a new application arrives (their in-app
  notification is created by the post_save signal in core/signals.py);
- a confirmed member gets an invite link to set their own password.

Emails are sent in the request, bounded by settings.EMAIL_TIMEOUT. A failed
email never undoes the application or the account: it is logged (ids only),
the in-app notification remains, and an invite can be resent by an admin.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail

from apps.authentication.models import User
from apps.authentication.tokens import issue_password_token
from core.frontend_links import frontend_url

logger = logging.getLogger(__name__)

INVITE_LIFETIME_HOURS = 72
INVITE_LIFETIME = timedelta(hours=INVITE_LIFETIME_HOURS)
MEMBER_REQUESTS_ADMIN_PATH = '/admin/member-requests'


def email_admins_of_new_request(church, member_request):
    """
    Email every active admin of `church` about a new application.

    Only the applicant's name goes into the email; their contact details,
    address and date of birth stay in the dashboard.
    """
    admins = list(User.objects.filter(church=church, role='admin', is_active=True))
    if not admins:
        logger.warning('member_request_no_admins', extra={'church_id': church.pk})
        return

    message = f'{member_request.name} has applied to join {church.name}.'
    review_link = frontend_url(MEMBER_REQUESTS_ADMIN_PATH, church)
    for admin in admins:
        try:
            send_mail(
                subject=f'New membership application from {member_request.name}',
                message=(
                    f"Hello {admin.name},\n\n"
                    f"{message}\n\n"
                    f"Review it in {settings.PLATFORM_NAME}:\n{review_link}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
            )
        except Exception:
            logger.exception(
                'member_request_admin_email_failed',
                extra={'church_id': church.pk, 'admin_id': admin.pk,
                       'member_request_id': member_request.pk},
            )


def send_member_invite(user, church):
    """
    Email `user` a single-use link, valid for INVITE_LIFETIME_HOURS, to set
    their password. Any earlier invite or reset link stops working.
    Returns True if the email was handed to the mail server.
    """
    token = issue_password_token(user, INVITE_LIFETIME)
    invite_link = frontend_url(f'/reset-password?token={token}&invite=1', church)
    try:
        send_mail(
            subject=f'Activate your {settings.PLATFORM_NAME} account for {church.name}',
            message=(
                f"Hello {user.name},\n\n"
                f"Your membership of {church.name} has been confirmed. "
                "Set your password to activate your account. "
                f"This link works once and expires in {INVITE_LIFETIME_HOURS} hours:\n\n"
                f"{invite_link}\n\n"
                "If the link has expired, ask your church office to resend it."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception:
        logger.exception('member_invite_email_failed', extra={'user_id': user.pk, 'church_id': church.pk})
        return False
    return True
