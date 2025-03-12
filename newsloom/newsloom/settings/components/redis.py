from newsloom.contrib.env import get_env_var

REDIS_HOST = get_env_var("REDIS_HOST", default="localhost")
REDIS_PORT = get_env_var("REDIS_PORT", type=int, default=6379)
REDIS_DB_CELERY = get_env_var("REDIS_DB_CELERY", type=int, default=8)
