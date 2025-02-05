"""Pytest configuration for newsloom tests."""

import django
from django.conf import settings


def pytest_configure():
    """Configure Django settings for tests."""
    settings.configure(
        DEBUG=False,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "streams",
            "agents",
            "sources",
            "mediamanager",
        ],
        USE_TZ=True,
        TIME_ZONE="UTC",
        # nosec B106
        SECRET_KEY="test-key-not-for-production",
    )
    django.setup()
