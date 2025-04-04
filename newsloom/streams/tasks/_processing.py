import logging
from functools import wraps

from django.conf import settings
from django.utils import timezone

from streams.exceptions import StreamProcessingError
from streams.models import Stream, StreamLog

logger = logging.getLogger(__name__)


def stream_processing(stream_type: str | None  = None):
    def decorator(task_func):
        @wraps(task_func)
        def wrapper(self, stream_id, *args, **kwargs):
            try:
                stream: Stream = Stream.objects.get(pk=stream_id)
                if stream_type and stream.stream_type != stream_type:
                    raise StreamProcessingError(f"Stream invalid stream type: {stream.stream_type}")

                stream_log = StreamLog.objects.create(stream=stream, status="running")
                try:
                    result = task_func(self, stream, *args, **kwargs)

                    # Update log for success
                    stream_log.status = "success"
                    stream_log.result = result
                    stream_log.completed_at = timezone.now()
                    stream_log.save()

                    return result
                except Exception as exc:
                    # Update log for failed

                    stream_log.status = "failed"
                    stream_log.error_message = str(exc)
                    stream_log.completed_at = timezone.now()
                    stream_log.save()

                    raise self.retry(
                        exc=exc, countdown=settings.STREAM_SCHEDULER_RETRY_DELAY,
                        max_retries=settings.STREAM_SCHEDULER_MAX_RETRIES
                    )
            except Stream.DoesNotExist:
                raise StreamProcessingError(f"Stream does not exist")
        return wrapper
    return decorator
