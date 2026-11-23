"""
Server-side enforcement of the parts of Flocktend a church has switched off.

The menu hides switched-off modules; this makes their API refuse too, so a
switched-off module can't be used by calling its endpoints directly.

A module counts as on unless the church has explicitly switched it off, which
keeps churches created before modules existed (no setting saved) working as
before. This matches `isModuleOn` in the frontend.
"""
from rest_framework import permissions

from .setup_rules import MODULE_KEYS

MODULE_LABELS = {
    'giving': 'Giving',
    'dues': 'Dues',
    'events': 'Events',
    'prayerRequests': 'Prayer requests',
    'volunteers': 'Volunteers',
    'ministries': 'Ministries',
    'serviceRequests': 'Service requests',
    'altarCalls': 'Altar calls',
}


def module_is_on(church, key):
    modules = (church.features or {}).get('modules')
    if not isinstance(modules, dict):
        return True
    return modules.get(key) is not False


def requires_module(key):
    """A DRF permission that refuses requests while `key` is switched off for the request's church."""
    if key not in MODULE_KEYS:
        raise ValueError(f'Unknown module: {key}')

    class ModuleSwitchedOn(permissions.BasePermission):
        message = f"{MODULE_LABELS[key]} isn't switched on for this church."

        def has_permission(self, request, view):
            # Without a church (public schema) there is no module setting to apply.
            church = getattr(request, 'church', None)
            return church is None or module_is_on(church, key)

    ModuleSwitchedOn.__name__ = f'RequiresModule_{key}'
    return ModuleSwitchedOn
