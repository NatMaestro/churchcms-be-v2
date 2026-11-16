"""
Who a request is about, for data that belongs to individual church members.

Church staff (church admins and platform superadmins) see and manage every
member's records. A member sees only their own, and acts only for
themselves: any member id they send is ignored.

Member rows live in the church's schema and link to the login through
Member.user, so "my record" is looked up by user within the current church.
"""
from apps.members.models import Member


def is_church_staff(user):
    return bool(user and user.is_authenticated and (user.is_church_admin or user.is_superadmin))


def member_for(user):
    """The current church's Member record for this login, or None."""
    if not (user and user.is_authenticated):
        return None
    return Member.objects.filter(user=user).first()


def acting_member(request):
    """
    The member a join / register / leave request is for.
    Staff may name one with `member_id`; everyone else acts for themselves.
    Returns None when there is no such member.
    """
    member_id = request.data.get('member_id')
    if is_church_staff(request.user) and member_id:
        return Member.objects.filter(pk=member_id).first()
    return member_for(request.user)
