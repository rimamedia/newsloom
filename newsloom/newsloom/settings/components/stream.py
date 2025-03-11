from newsloom.contrib.env import get_env_var

STREAM_SCHEDULER_SLEEP_INTERVAL = get_env_var('STREAM_SCHEDULER_SLEEP_INTERVAL', int, 60)
STREAM_SCHEDULER_BATCH_SIZE = get_env_var('STREAM_SCHEDULER_BATCH_SIZE', int, 10)
STREAM_SCHEDULER_MAX_RETRIES = get_env_var('STREAM_SCHEDULER_MAX_RETRIES', int, 3)
STREAM_SCHEDULER_RETRY_DELAY = get_env_var('STREAM_SCHEDULER_RETRY_DELAY', int, 300)