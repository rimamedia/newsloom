from logging import getLogger

from django.conf import settings

from newsloom.celery import app
from streams.models import Stream


logger = getLogger(__name__)


@app.task(bind=True)
def process_stream(self, stream_id: int, delay:bool=True) -> None:
    """Process a single stream."""
    try:
        # stream = Stream.objects.filter(status__in=['active', 'failed']).get(pk=stream_id)
        stream = Stream.objects.get(pk=stream_id)
        stream.execute_task(delay=delay)
    except Stream.DoesNotExist:
        logger.error(f"Stream {stream_id} does not exist")
    except Exception as exc:
        raise self.retry(
            exc=exc, countdown=settings.STREAM_SCHEDULER_RETRY_DELAY, max_retries=settings.STREAM_SCHEDULER_MAX_RETRIES
        )
