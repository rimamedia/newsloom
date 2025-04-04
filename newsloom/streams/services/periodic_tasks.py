from functools import lru_cache

from django_celery_beat.models import CrontabSchedule, PeriodicTask

from streams.models import Stream

STREAM_FREQUENCY_TO_CRONTAB = {
    "5min": {'minute': '*/5'},
    "15min": {'minute': '*/15'},
    "30min": {'minute': '*/30'},
    "1hour": {'minute': '3'},
    "6hours": {'minute': '3', 'hour': "*/6"},
    "12hours": {'minute': '3', 'hour': "*/12"},
    "daily": {'minute': '3', 'hour': "0"},
}


@lru_cache()
def get_crontab_schedule_by_stream_frequency(frequency: str) -> CrontabSchedule:
    crontab, _ = CrontabSchedule.objects.get_or_create(**STREAM_FREQUENCY_TO_CRONTAB[frequency])
    return crontab


def get_periodic_task_by_stream(stream: Stream) -> PeriodicTask | None:
    return PeriodicTask.objects.filter(
        task='streams.tasks._process.process_stream', args=f"[{stream.id}]"
    ).first()


def stream_to_periodic_task(stream: Stream) -> PeriodicTask:
    periodic_task = get_periodic_task_by_stream(stream)
    if not periodic_task:
        periodic_task = PeriodicTask(task='streams.tasks._process.process_stream', args=f"[{stream.id}]")
    periodic_task.name=f'{stream.id} {stream}'
    periodic_task.crontab=get_crontab_schedule_by_stream_frequency(stream.frequency)
    periodic_task.save()
    return periodic_task
