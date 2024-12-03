import logging

from django.db import transaction
from django.utils import timezone

from .models import Stream

logger = logging.getLogger(__name__)


class StreamScheduler:
    """Manages the execution of Stream tasks."""

    @classmethod
    def execute_due_tasks(cls):
        """Execute all tasks that are due to run."""
        try:
            with transaction.atomic():
                due_streams = Stream.objects.filter(
                    status="active", next_run__lte=timezone.now()
                ).select_for_update(skip_locked=True)

                for stream in due_streams:
                    try:
                        stream.execute_task()
                    except Exception as e:
                        logger.exception(f"Failed to execute stream {stream.id}: {e}")
                        # Continue with next stream even if one fails
                        continue

        except Exception as e:
            logger.exception(f"Error in execute_due_tasks: {e}")

    @classmethod
    def retry_failed_tasks(cls):
        """Retry failed tasks."""
        try:
            with transaction.atomic():
                failed_streams = Stream.objects.filter(
                    status="failed"
                ).select_for_update(skip_locked=True)

                for stream in failed_streams:
                    try:
                        stream.execute_task()
                    except Exception as e:
                        logger.exception(f"Failed to retry stream {stream.id}: {e}")
                        # Continue with next stream even if one fails
                        continue

        except Exception as e:
            logger.exception(f"Error in retry_failed_tasks: {e}")
