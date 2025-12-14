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
        from django.db import connection
        from apps.churches.models import Church
        
        # Get church from tenant context or creator's church
        church = None
        try:
            # Try to get church from current tenant
            tenant = connection.get_tenant()
            if tenant and isinstance(tenant, Church):
                church = tenant
        except:
            pass
        
        # Fallback: get church from creator
        if not church and instance.created_by and instance.created_by.church:
            church = instance.created_by.church
        
        if not church:
            # Can't determine church, skip notification creation
            return
        
        # Get all members of the church (in tenant schema, all users are members of this church)
        users = User.objects.filter(
            church=church,
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
        from django.db import connection
        from apps.churches.models import Church
        
        # Get church from tenant context or creator's church
        church = None
        try:
            # Try to get church from current tenant
            tenant = connection.get_tenant()
            if tenant and isinstance(tenant, Church):
                church = tenant
        except Exception as e:
            # Fallback: get church from creator
            if instance.created_by and instance.created_by.church:
                church = instance.created_by.church
            else:
                print(f"Warning: Could not determine church for announcement {instance.id}. Error: {e}")
                return  # Cannot create notifications without a church context
        
        # Fallback: get church from creator if tenant context failed
        if not church and instance.created_by and instance.created_by.church:
            church = instance.created_by.church
        
        if not church:
            print(f"Warning: No church context found for announcement {instance.id}. Skipping notification creation.")
            return
        
        # Determine recipients based on target_audience
        if instance.target_audience == 'all':
            users = User.objects.filter(church=church, is_active=True)
        elif instance.target_audience == 'members':
            users = User.objects.filter(church=church, role='member', is_active=True)
        elif instance.target_audience == 'leaders':
            users = User.objects.filter(church=church, role__in=['admin', 'leader'], is_active=True)
        else:
            # Default to members
            users = User.objects.filter(church=church, role='member', is_active=True)
        
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


@receiver(post_save, sender='members.MemberRequest')
def create_member_request_notifications(sender, instance, created, **kwargs):
    """
    Auto-create notifications when someone submits a membership request.
    Notify admins when:
    1. New request is submitted (pending)
    2. Request is approved and needs final confirmation
    """
    from apps.notifications.models import Notification
    from apps.authentication.models import User
    
    if not instance.church:
        return
    
    # Get admins for this church
    # Note: MemberRequest is in public schema, so we need to query public users
    admins = User.objects.filter(
        church=instance.church,
        role='admin',
        is_active=True
    )
    
    notifications = []
    
    if created:
        # New request submitted
        for admin in admins:
            notifications.append(
                Notification(
                    user=admin,
                    type='member_request',
                    title='New Membership Request',
                    message=f"{instance.name} ({instance.email}) has requested to join your church",
                    priority='high',
                    metadata={
                        'request_id': str(instance.id),
                        'request_type': 'membership_application',
                        'status': instance.status,
                    }
                )
            )
    elif instance.status == 'approved' and kwargs.get('update_fields') and 'status' in kwargs['update_fields']:
        # Request approved - notify for final confirmation
        for admin in admins:
            notifications.append(
                Notification(
                    user=admin,
                    type='member_request',
                    title='Membership Request Approved - Awaiting Confirmation',
                    message=f"{instance.name}'s membership request has been approved and is ready for final confirmation",
                    priority='normal',
                    metadata={
                        'request_id': str(instance.id),
                        'request_type': 'membership_application',
                        'status': instance.status,
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






