from newsloom.contrib.env import get_env_var

BEDROCK_AWS_ACCESS_KEY_ID = get_env_var("BEDROCK_AWS_ACCESS_KEY_ID", default=None)
BEDROCK_AWS_SECRET_ACCESS_KEY = get_env_var("BEDROCK_AWS_SECRET_ACCESS_KEY", default=None)
BEDROCK_AWS_REGION = get_env_var("BEDROCK_AWS_REGION", default="us-west-2")
