"""
Rules shared by church sign-up, the live web-address check, and the
church's feature switches, so every entry point applies the same ones.
"""
import re

SUBDOMAIN_MIN_LENGTH = 3
SUBDOMAIN_MAX_LENGTH = 40
# Lowercase letters and digits, single hyphens between them (valid in a hostname).
SUBDOMAIN_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
# Addresses the platform uses or could be mistaken for it.
RESERVED_SUBDOMAINS = frozenset({
    'www', 'api', 'admin', 'app', 'mail', 'email', 'smtp', 'ftp', 'superadmin', 'platform',
    'login', 'auth', 'account', 'accounts', 'signup', 'register', 'onboarding', 'dashboard',
    'support', 'help', 'docs', 'status', 'blog', 'static', 'assets', 'media', 'cdn',
    'test', 'dev', 'staging', 'demo', 'flocktend', 'faithflow', 'faithflow360', 'public',
})

# The parts of Flocktend a church can switch on or off (stored under features['modules']).
# Members, settings and the dashboard are always on.
MODULE_KEYS = ('giving', 'dues', 'events', 'prayerRequests', 'volunteers', 'ministries',
               'serviceRequests', 'altarCalls')


def normalize_subdomain(value):
    return (value or '').strip().lower()


def subdomain_problem(subdomain):
    """Why this web address can't be used (format or reserved), or None. Doesn't check if it's taken."""
    if not (SUBDOMAIN_MIN_LENGTH <= len(subdomain) <= SUBDOMAIN_MAX_LENGTH):
        return f'Use {SUBDOMAIN_MIN_LENGTH} to {SUBDOMAIN_MAX_LENGTH} characters.'
    if not SUBDOMAIN_PATTERN.match(subdomain):
        return 'Use only letters, numbers and single hyphens (no spaces or other characters).'
    if subdomain in RESERVED_SUBDOMAINS:
        return 'This address is reserved. Please choose another.'
    return None


def clean_modules(value):
    """A {module: bool} dict with known keys only; raises ValueError otherwise."""
    if not isinstance(value, dict):
        raise ValueError('Modules must be an object of on/off switches.')
    unknown = sorted(set(value) - set(MODULE_KEYS))
    if unknown:
        raise ValueError(f'Unknown modules: {", ".join(unknown)}.')
    if not all(isinstance(on, bool) for on in value.values()):
        raise ValueError('Each module must be true or false.')
    return dict(value)
