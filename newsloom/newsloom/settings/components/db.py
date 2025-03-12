from newsloom.contrib.env import get_env_var

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_env_var("DB_NAME", default='newsloom'),
        "USER": get_env_var("DB_USER", default='postgres'),
        "PASSWORD": get_env_var("DB_PASSWORD", default=None),
        "HOST": get_env_var("DB_HOST", default="localhost"),
        "PORT": get_env_var("DB_PORT", int, default=5432),
        "OPTIONS": {
            "options": "-c timezone=UTC",
            "sslmode": get_env_var("DJANGO_DB_SSLMODE", default="require"),
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"