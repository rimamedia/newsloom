from newsloom.contrib.env import get_env_var

GOOGLE_PRIVATE_KEY = get_env_var('GOOGLE_PRIVATE_KEY', default="").strip('"\'').replace('\\n', '\n')
GOOGLE_PROJECT_ID = get_env_var("GOOGLE_PROJECT_ID", default="").strip('"')
GOOGLE_PRIVATE_KEY_ID = get_env_var("GOOGLE_PRIVATE_KEY_ID", default="").strip('"')
GOOGLE_CLIENT_EMAIL = get_env_var("GOOGLE_CLIENT_EMAIL", default="").strip('"')
GOOGLE_CLIENT_ID = get_env_var("GOOGLE_CLIENT_ID", default="").strip('"')
GOOGLE_CLIENT_X509_CERT_URL = get_env_var("GOOGLE_CLIENT_X509_CERT_URL", default="").strip('"')