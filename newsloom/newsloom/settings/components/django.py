
from newsloom.contrib.env import get_env_var

from newsloom.settings import BASE_DIR


DEBUG = get_env_var("DEBUG", bool, False)

SECRET_KEY = get_env_var("DJANGO_SECRET_KEY", default="unsafe-secret-key")

ALLOWED_HOSTS = get_env_var("ALLOWED_HOSTS", list[str], default=['*'])

PROJECT_APPS = [
    "agents",

    "chat",
    "frontend",
    "mediamanager",
    "sources",
    "streams",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "channels",
    "corsheaders",
    "django_filters",
    'django_celery_beat',

    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",

] + PROJECT_APPS


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "newsloom/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ROOT_URLCONF = "newsloom.urls"

ASGI_APPLICATION = "newsloom.asgi.application"
WSGI_APPLICATION = "newsloom.wsgi.application"