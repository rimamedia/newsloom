from newsloom.contrib.env import get_env_var

ARTICLEAN_API_KEY = get_env_var("ARTICLEAN_API_KEY", default="")
ARTICLEAN_API_URL = get_env_var("ARTICLEAN_API_URL", default="")
