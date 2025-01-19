import logging
import time
from typing import List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from streams.models import Stream, StreamExecutionStats

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_SLEEP_INTERVAL = 60  # seconds
DEFAULT_ERROR_SLEEP = 5  # seconds
DEFAULT_BATCH_SIZE = 10
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 300  # 5 minutes


class Command(BaseCommand):
    help = "Runs streams that are due for execution with improved reliability and performance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sleep-interval",
            type=int,
            default=getattr(
                settings, "STREAM_SCHEDULER_SLEEP_INTERVAL", DEFAULT_SLEEP_INTERVAL
            ),
            help="Sleep interval between checks in seconds",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=getattr(
                settings, "STREAM_SCHEDULER_BATCH_SIZE", DEFAULT_BATCH_SIZE
            ),
            help="Number of streams to process in parallel",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=getattr(
                settings, "STREAM_SCHEDULER_MAX_RETRIES", DEFAULT_MAX_RETRIES
            ),
            help="Maximum number of retries for failed streams",
        )
        parser.add_argument(
            "--retry-delay",
            type=int,
            default=getattr(
                settings, "STREAM_SCHEDULER_RETRY_DELAY", DEFAULT_RETRY_DELAY
            ),
            help="Delay between retries in seconds",
        )

    def get_due_streams(self, batch_size: int) -> List[Stream]:
        """Get streams that are due for execution."""
        now = timezone.now()

        # Get all streams that should be executed
        due_streams = list(
            Stream.objects.filter(
                # Include both active and failed streams that are due
                status__in=["active", "failed"],
                next_run__lte=now,
            )
            .select_related("source", "media")
            .order_by("next_run")[:batch_size]
        )

        # Log information about found streams
        if due_streams:
            logger.info(f"Found {len(due_streams)} streams due for execution:")
            for stream in due_streams:
                logger.info(
                    f"Stream '{stream.name}' (ID: {stream.id}) - "
                    f"Status: {stream.status}, "
                    f"Next run: {stream.next_run}, "
                    f"Last run: {stream.last_run}, "
                    f"Frequency: {stream.frequency}"
                )
        else:
            # Log all streams to help diagnose why none are being picked up
            all_streams = Stream.objects.all()
            logger.info("No due streams found. Current streams in database:")
            for stream in all_streams:
                logger.info(
                    f"Stream '{stream.name}' (ID: {stream.id}) - "
                    f"Status: {stream.status}, "
                    f"Next run: {stream.next_run}, "
                    f"Last run: {stream.last_run}, "
                    f"Frequency: {stream.frequency}"
                )

        return due_streams

    def process_single_stream(
        self, stream: Stream, stats: StreamExecutionStats, max_retries: int
    ) -> None:
        """Process a single stream with retry logic."""
        retry_count = 0
        while retry_count <= max_retries:
            try:
                # Execute the task directly without transaction wrapping
                stream.execute_task()
                stats.streams_succeeded += 1
                stats.save(update_fields=["streams_succeeded"])
                logger.info(f"Stream {stream.name} executed successfully")
                break
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    retry_delay = self.calculate_retry_delay(retry_count)
                    logger.warning(
                        f"Retry {retry_count}/{max_retries} for stream {stream.name} "
                        f"after {retry_delay} seconds. Error: {str(e)}"
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        f"Stream {stream.name} failed after {max_retries} retries: {str(e)}",
                        exc_info=True,
                    )
                    stats.streams_failed += 1
                    stats.save(update_fields=["streams_failed"])

    def process_streams(
        self, streams: List[Stream], stats: StreamExecutionStats, max_retries: int
    ) -> None:
        """Process a batch of streams."""
        for stream in streams:
            self.process_single_stream(stream, stats, max_retries)

    def calculate_retry_delay(self, retry_count: int) -> int:
        """Calculate exponential backoff delay."""
        return min(DEFAULT_RETRY_DELAY * (2 ** (retry_count - 1)), 3600)  # Max 1 hour

    def check_scheduler_health(self) -> Optional[str]:
        """Check scheduler health based on recent execution stats."""
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        recent_stats = StreamExecutionStats.objects.filter(
            execution_start__gte=one_hour_ago
        ).order_by("-execution_start")[:10]

        if not recent_stats.exists():
            return "No recent executions found"

        failure_rate = sum(s.streams_failed for s in recent_stats) / max(
            sum(s.streams_attempted for s in recent_stats), 1
        )
        if failure_rate > 0.5:  # More than 50% failure rate
            return f"High failure rate: {failure_rate:.2%}"

        return None

    def handle(self, *args, **options):
        self.stdout.write("Starting stream scheduler with improved configuration...")
        logger.info("Stream scheduler started")

        # Log timezone information to help diagnose timing issues
        logger.info(f"Current timezone: {timezone.get_current_timezone_name()}")
        logger.info(f"Current time: {timezone.now()}")

        # Reactivate any failed streams on startup
        Stream.reactivate_failed_streams()
        logger.info("Reactivated failed streams")

        sleep_interval = options["sleep_interval"]
        batch_size = options["batch_size"]
        max_retries = options["max_retries"]

        logger.info(
            f"Scheduler configuration: sleep_interval={sleep_interval}s, "
            f"batch_size={batch_size}, max_retries={max_retries}"
        )

        while True:
            try:
                # Create execution stats
                stats = StreamExecutionStats.objects.create()
                logger.info(f"Starting execution cycle at {stats.execution_start}")

                # Get due streams
                due_streams = self.get_due_streams(batch_size)

                if due_streams:
                    # Update stats before processing
                    stats.streams_attempted = len(due_streams)
                    stats.save()

                    # Process the streams
                    self.process_streams(due_streams, stats, max_retries)

                    # Log final results
                    total = stats.streams_succeeded + stats.streams_failed
                    logger.info(
                        f"Stream execution results:\n"
                        f"Total streams picked up: {stats.streams_attempted}\n"
                        f"Successfully completed: {stats.streams_succeeded}\n"
                        f"Failed: {stats.streams_failed}\n"
                        f"Total processed: {total}"
                    )

                # Update stats
                stats.execution_end = timezone.now()
                stats.save()
                stats.calculate_stats()

                duration = stats.execution_end - stats.execution_start
                logger.info(
                    f"Execution cycle completed in {duration.total_seconds():.2f} seconds"
                )

                # Check scheduler health
                health_issue = self.check_scheduler_health()
                if health_issue:
                    logger.warning(f"Scheduler health check: {health_issue}")

                # Sleep until next check
                time.sleep(sleep_interval)

            except Exception as e:
                logger.exception(f"Critical error in stream scheduler: {e}")
                time.sleep(DEFAULT_ERROR_SLEEP)
