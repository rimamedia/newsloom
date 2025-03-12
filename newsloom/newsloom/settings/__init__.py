from pathlib import Path

from split_settings.tools import optional, include

BASE_DIR = Path(__file__).resolve().parent.parent

SENTRY_DSN = None

_base_settings = (
    'components/django.py',
    'components/account.py',
    'components/api.py',
    'components/articlean.py',
    'components/bedrock.py',
    'components/celery.py',
    'components/channel.py',
    'components/db.py',
    'components/google.py',
    'components/locale.py',
    'components/log.py',
    'components/secure.py',
    'components/sentry.py',
    'components/slack.py',
    'components/static.py',
    'components/stream.py',
    'components/telegram.py',

    optional('settings_local.py'),
    'components/_last.py',
)

include(*_base_settings)
