from newsloom.contrib.env import get_env_var

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = [o.strip() for o in get_env_var('CSRF_TRUSTED_ORIGINS',list[str], '') if o.strip()]

CSRF_COOKIE_SECURE =  get_env_var("CSRF_COOKIE_SECURE", bool, True)
CSRF_USE_SESSIONS = get_env_var("CSRF_USE_SESSIONS", bool, True)
CSRF_COOKIE_HTTPONLY = True


# CORS settings
CORS_ALLOW_CREDENTIALS = True