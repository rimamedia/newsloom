import logging
import time
from typing import List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
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
        return list(
            Stream.objects.filter(
                status="active", next_run__lte=timezone.now()
            ).select_related("source", "media")[:batch_size]
        )

    def process_streams(
        self, streams: List[Stream], stats: StreamExecutionStats, max_retries: int
    ) -> None:
        """Process a batch of streams with retry logic."""
        for stream in streams:
            retry_count = 0
            while retry_count <= max_retries:
                try:
                    # Use the stream's execute_task method which handles logging
                    stream.execute_task()
                    stats.streams_succeeded += 1
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

        sleep_interval = options["sleep_interval"]
        batch_size = options["batch_size"]
        max_retries = options["max_retries"]

        while True:
            try:
                with transaction.atomic():
                    # Create execution stats
                    stats = StreamExecutionStats.objects.create()

                    # Get and process due streams
                    due_streams = self.get_due_streams(batch_size)
                    stats.streams_attempted = len(due_streams)

                    if due_streams:
                        self.process_streams(due_streams, stats, max_retries)

                    # Update stats
                    stats.execution_end = timezone.now()
                    stats.save()
                    stats.calculate_stats()

                # Check scheduler health
                health_issue = self.check_scheduler_health()
                if health_issue:
                    logger.warning(f"Scheduler health check: {health_issue}")

                # Sleep until next check
                time.sleep(sleep_interval)

            except Exception as e:
                logger.exception(f"Critical error in stream scheduler: {e}")
                time.sleep(DEFAULT_ERROR_SLEEP)
