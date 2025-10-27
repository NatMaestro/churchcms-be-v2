"""
Django signals for auto-creating notifications and tracking events.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender='events.Event')
def create_event_notifications(sender, instance, created, **kwargs):
    """
    Auto-create notifications when an event is created.
    Notify all church members.
    """
    if created:
        from apps.notifications.models import Notification
        from apps.authentication.models import User
        
        # Get all members of the church
        users = User.objects.filter(
            church=instance.church,
            role='member',
            is_active=True
        )
        
        # Determine priority based on event date
        hours_until = (instance.date - timezone.now()).total_seconds() / 3600
        priority = 'urgent' if hours_until < 48 else 'normal'
        
        # Create notifications for all members
        notifications = []
        for user in users:
            notifications.append(
                Notification(
                    user=user,
                    type='event',
                    title=f"New Event: {instance.title}",
                    message=f"{instance.title} has been scheduled for {instance.date.strftime('%B %d, %Y at %I:%M %p')} at {instance.location}",
                    priority=priority,
                    metadata={
                        'event_id': str(instance.id),
                        'event_title': instance.title,
                        'event_date': instance.date.isoformat(),
                    }
                )
            )
        
        if notifications:
            Notification.objects.bulk_create(notifications)


@receiver(post_save, sender='announcements.Announcement')
def create_announcement_notifications(sender, instance, created, **kwargs):
    """
    Auto-create notifications when announcement is posted.
    """
    if created and instance.is_active:
        from apps.notifications.models import Notification
        from apps.authentication.models import User
        
        # Determine recipients based on target_audience
        if instance.target_audience == 'all':
            users = User.objects.filter(church=instance.church, is_active=True)
        elif instance.target_audience == 'members':
            users = User.objects.filter(church=instance.church, role='member', is_active=True)
        else:
            users = User.objects.filter(church=instance.church, role='member', is_active=True)
        
        # Create notifications
        notifications = []
        for user in users:
            notifications.append(
                Notification(
                    user=user,
                    type='announcement',
                    title=f"New Announcement: {instance.title}",
                    message=instance.content[:200] + '...' if len(instance.content) > 200 else instance.content,
                    priority=instance.priority,
                    metadata={
                        'announcement_id': str(instance.id),
                        'announcement_title': instance.title,
                    }
                )
            )
        
        if notifications:
            Notification.objects.bulk_create(notifications)


@receiver(post_save, sender='requests.ServiceRequest')
def create_request_notifications(sender, instance, created, **kwargs):
    """
    Auto-create notifications when member submits service request.
    Notify admins.
    """
    if created:
        from apps.notifications.models import Notification
        from apps.authentication.models import User
        
        # Notify admins
        admins = User.objects.filter(
            church=instance.member.church,
            role='admin',
            is_active=True
        )
        
        notifications = []
        for admin in admins:
            notifications.append(
                Notification(
                    user=admin,
                    type='member_request',
                    title='New Service Request',
                    message=f"{instance.member.full_name} submitted a {instance.type} request",
                    priority='high',
                    metadata={
                        'request_id': str(instance.id),
                        'member_id': str(instance.member.id),
                        'request_type': instance.type,
                    }
                )
            )
        
        if notifications:
            Notification.objects.bulk_create(notifications)


@receiver(post_save, sender='payments.Payment')
def create_payment_notifications(sender, instance, created, **kwargs):
    """
    Auto-create notifications for payments.
    """
    if created and instance.status == 'completed':
        from apps.notifications.models import Notification
        from apps.authentication.models import User
        
        # Notify the member
        if instance.member and instance.member.user:
            Notification.objects.create(
                user=instance.member.user,
                type='payment',
                title='Payment Confirmed',
                message=f"Your {instance.type} payment of {instance.currency} {instance.amount} has been confirmed",
                priority='normal',
                metadata={
                    'payment_id': str(instance.id),
                    'amount': str(instance.amount),
                    'type': instance.type,
                }
            )
        
        # Notify admins
        admins = User.objects.filter(
            church=instance.member.church,
            role='admin',
            is_active=True
        )
        
        for admin in admins:
            Notification.objects.create(
                user=admin,
                type='payment',
                title='Payment Received',
                message=f"{instance.member.full_name} made a {instance.type} payment of {instance.currency} {instance.amount}",
                priority='low',
                metadata={
                    'payment_id': str(instance.id),
                    'member_id': str(instance.member.id),
                }
            )


@receiver(post_save, sender='prayers.PrayerRequest')
def create_prayer_request_notifications(sender, instance, created, **kwargs):
    """
    Auto-create notifications for prayer requests.
    """
    if created:
        from apps.notifications.models import Notification
        from apps.authentication.models import User
        
        # Notify admins and prayer team
        recipients = User.objects.filter(
            church=instance.member.church if instance.member else None,
            role__in=['admin'],
            is_active=True
        )
        
        requester_name = instance.member.full_name if instance.member else instance.requester_name or 'Anonymous'
        
        notifications = []
        for user in recipients:
            notifications.append(
                Notification(
                    user=user,
                    type='prayer',
                    title='New Prayer Request',
                    message=f"{requester_name} submitted a prayer request: {instance.title}",
                    priority='normal' if instance.urgency == 'normal' else 'high',
                    metadata={
                        'prayer_id': str(instance.id),
                        'category': instance.category,
                        'urgency': instance.urgency,
                    }
                )
            )
        
        if notifications:
            Notification.objects.bulk_create(notifications)

