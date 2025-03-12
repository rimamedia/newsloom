from newsloom.contrib.env import get_env_var

from newsloom.settings.components import redis as redis_settings
from newsloom.settings.components.locale import TIME_ZONE

CELERY_WORKERS = get_env_var("CELERY_WORKERS", type=int, default=1)


CELERY = {
    'broker_url': f'redis://{redis_settings.REDIS_HOST}:{redis_settings.REDIS_PORT}/{redis_settings.REDIS_DB_CELERY}',
    'enable_utc': False,
    'timezone': TIME_ZONE,
    'accept_content': ['json', 'pickle'],

    'task_serializer': 'pickle',
    'task_ignore_result': True,
    'task_acks_late': True,

    'result_serializer': 'pickle',
    'result_expires': 60 * 2,

    'beat_scheduler': 'django_celery_beat.schedulers.DatabaseScheduler',

    'worker_pool_restarts': True,
    'worker_max_tasks_per_child': 20,
    'worker_max_memory_per_child': 12001,
    'worker_prefetch_multiplier': 1,
    'worker_concurrency': CELERY_WORKERS,

    'worker_send_task_events': True,
    'task_send_sent_event': True,

    'broker_connection_retry_on_startup': True,
    'broker_channel_error_retry': True,
}
