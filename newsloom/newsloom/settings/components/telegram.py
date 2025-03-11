from newsloom.contrib.env import get_env_var

TELEGRAM_BOT_TOKEN = get_env_var("TELEGRAM_BOT_TOKEN", default=None)
