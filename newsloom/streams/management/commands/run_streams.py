import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone
from streams.models import Stream, StreamExecutionStats, StreamLog
from streams.tasks import get_task_function

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs streams that are due for execution"

    def execute_stream(self, stream):
        """Execute a single stream and update its status."""
        try:
            # Get task function
            task_function = get_task_function(stream.stream_type)
            if not task_function:
                raise ValueError(
                    f"No task function found for type: {stream.stream_type}"
                )

            # Execute task
            result = task_function(stream_id=stream.id, **stream.configuration)

            # Update stream timing
            now = timezone.now()
            stream.last_run = now
            stream.next_run = stream.get_next_run_time()
            stream.save()

            # Log success
            StreamLog.objects.create(
                stream=stream, status="success", result=result, completed_at=now
            )
            logger.info(f"Successfully executed stream: {stream.name}")

        except Exception as e:
            error_msg = f"Failed to execute stream {stream.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Log failure
            StreamLog.objects.create(
                stream=stream,
                status="failed",
                error_message=str(e),
                completed_at=timezone.now(),
            )

            # Mark stream as failed
            stream.status = "failed"
            stream.save()

    def handle(self, *args, **options):
        self.stdout.write("Starting stream scheduler...")
        logger.info("Stream scheduler started")

        while True:
            try:
                # Create execution stats for this run
                stats = StreamExecutionStats.objects.create()

                try:
                    # Get all active streams that are due to run
                    due_streams = Stream.objects.filter(
                        status="active", next_run__lte=timezone.now()
                    )

                    stats.streams_attempted = due_streams.count()
                    stats.save(update_fields=["streams_attempted"])

                    # Execute each due stream
                    for stream in due_streams:
                        try:
                            self.execute_stream(stream)
                            stats.streams_succeeded += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to execute stream: {e}", exc_info=True
                            )
                            stats.streams_failed += 1
                        stats.save(
                            update_fields=["streams_succeeded", "streams_failed"]
                        )

                finally:
                    # Complete stats
                    stats.execution_end = timezone.now()
                    stats.calculate_stats()

                # Sleep for 60 seconds before next check
                time.sleep(60)

            except Exception as e:
                logger.exception(f"Error in stream scheduler: {e}")
                time.sleep(5)  # Short sleep on error before retry
