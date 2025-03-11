import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from newsloom.settings import SENTRY_DSN


if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=True,
        traces_sample_rate=1.0,
        _experiments={
            "continuous_profiling_auto_start": True,
        },
    )
