"""
Links to the web app that go out in emails (password reset, member invites,
admin alerts).

Each church uses the app at its own subdomain, e.g. https://olamchurch.faithflow360.com,
so a link for someone in a church opens on that church's site. The church site is
the FRONTEND_URL host with any leading "www." replaced by the church subdomain:

    FRONTEND_URL=https://www.faithflow360.com  ->  https://<subdomain>.faithflow360.com
    FRONTEND_URL=http://localhost:8080         ->  http://<subdomain>.localhost:8080

People without a church (platform superadmins) get FRONTEND_URL itself.
"""
from urllib.parse import urlsplit

from django.conf import settings

WWW_PREFIX = 'www.'


def frontend_url(path, church=None):
    """Absolute URL of `path` (starting with "/") on `church`'s site, or the main site."""
    base = settings.FRONTEND_URL.rstrip('/')
    subdomain = getattr(church, 'subdomain', '') if church is not None else ''
    if not subdomain:
        return f'{base}{path}'

    parts = urlsplit(base)
    host = parts.hostname or ''
    if host.startswith(WWW_PREFIX):
        host = host[len(WWW_PREFIX):]
    port = f':{parts.port}' if parts.port else ''
    return f'{parts.scheme}://{subdomain}.{host}{port}{path}'
