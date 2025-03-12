from newsloom.contrib.env import get_env_var

SLACK_BOT_TOKEN = get_env_var("SLACK_BOT_TOKEN", default=None)
SLACK_APP_TOKEN = get_env_var("SLACK_APP_TOKEN", default=None)