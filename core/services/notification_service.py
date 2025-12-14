"""
Notification service for creating and managing notifications.
"""

from apps.notifications.models import Notification
from apps.authentication.models import User


class NotificationService:
    """
    Service for creating and managing notifications.
    Centralizes notification logic.
    """
    
    @staticmethod
    def notify_user(user, title, message, notification_type='system', priority='normal', metadata=None):
        """
        Send notification to a single user.
        """
        return Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            metadata=metadata or {}
        )
    
    @staticmethod
    def notify_church(church, title, message, notification_type='system', priority='normal', metadata=None):
        """
        Send notification to all members of a church.
        """
        users = User.objects.filter(
            church=church,
            role='member',
            is_active=True
        )
        
        notifications = []
        for user in users:
            notifications.append(
                Notification(
                    user=user,
                    type=notification_type,
                    title=title,
                    message=message,
                    priority=priority,
                    metadata=metadata or {}
                )
            )
        
        return Notification.objects.bulk_create(notifications)
    
    @staticmethod
    def notify_admins(church, title, message, notification_type='system', priority='high', metadata=None):
        """
        Send notification to all admins of a church.
        """
        admins = User.objects.filter(
            church=church,
            role='admin',
            is_active=True
        )
        
        notifications = []
        for admin in admins:
            notifications.append(
                Notification(
                    user=admin,
                    type=notification_type,
                    title=title,
                    message=message,
                    priority=priority,
                    metadata=metadata or {}
                )
            )
        
        return Notification.objects.bulk_create(notifications)
    
    @staticmethod
    def notify_event_created(event):
        """Notify members about new event."""
        users = User.objects.filter(
            church=event.church,
            role='member',
            is_active=True
        )
        
        from django.utils import timezone
        hours_until = (event.date - timezone.now()).total_seconds() / 3600
        priority = 'urgent' if hours_until < 48 else 'normal'
        
        notifications = []
        for user in users:
            notifications.append(
                Notification(
                    user=user,
                    type='event',
                    title=f"New Event: {event.title}",
                    message=f"{event.title} - {event.date.strftime('%B %d, %Y at %I:%M %p')} at {event.location}",
                    priority=priority,
                    metadata={
                        'event_id': str(event.id),
                        'event_title': event.title,
                        'event_date': event.date.isoformat(),
                    }
                )
            )
        
        return Notification.objects.bulk_create(notifications)
    
    @staticmethod
    def notify_payment_received(payment):
        """Notify member and admins about payment."""
        notifications = []
        
        # Notify member
        if payment.member and payment.member.user:
            notifications.append(
                Notification(
                    user=payment.member.user,
                    type='payment',
                    title='Payment Confirmed',
                    message=f"Your {payment.type} payment of {payment.currency} {payment.amount} has been confirmed",
                    priority='normal',
                    metadata={
                        'payment_id': str(payment.id),
                        'amount': str(payment.amount),
                    }
                )
            )
        
        # Notify admins
        admins = User.objects.filter(
            church=payment.member.church,
            role='admin',
            is_active=True
        )
        
        for admin in admins:
            notifications.append(
                Notification(
                    user=admin,
                    type='payment',
                    title='Payment Received',
                    message=f"{payment.member.full_name} - {payment.type} {payment.currency} {payment.amount}",
                    priority='low',
                    metadata={
                        'payment_id': str(payment.id),
                        'member_id': str(payment.member.id),
                    }
                )
            )
        
        return Notification.objects.bulk_create(notifications)






