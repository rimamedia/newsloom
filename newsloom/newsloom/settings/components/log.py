LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    "loggers": {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.utils.autoreload': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.template': {
            'handlers': ['null'],
            'level': 'ERROR',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        "chat.message_processing": {
            "handlers": ["console",],
            "level": "INFO",
            "propagate": True,
        },
    },
    "root": {
        "handlers": ["console",],
        "level": "DEBUG",
    },
}
