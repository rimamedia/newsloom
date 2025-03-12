import logging
import multiprocessing
import random
import time
from typing import List

from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone
from streams.models import Stream, StreamExecutionStats

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 300  # 5 minutes


def calculate_retry_delay(retry_count: int) -> int:
    """Calculate exponential backoff delay with jitter."""
    base_delay = DEFAULT_RETRY_DELAY * (2 ** (retry_count - 1))
    jitter = random.uniform(0.8, 1.2)  # ±20% jitter
    return min(int(base_delay * jitter), 3600)  # Max 1 hour


def process_single_stream(stream_id: int, max_retries: int) -> bool:
    """Process a single stream with retry logic."""
    # Close any existing database connections before starting
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()

    success = False

    try:
        # Get fresh instance from the database
        stream = Stream.objects.get(id=stream_id)
        retry_count = 0

        while retry_count <= max_retries:
            try:
                # Execute the task directly without transaction wrapping
                stream.execute_task()
                # Refresh from db since execute_task updates the stream
                stream.refresh_from_db()
                logger.info(
                    f"Stream {stream.name} executed successfully (Next run: {stream.next_run})"
                )
                success = True
                break
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    retry_delay = calculate_retry_delay(retry_count)
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
    except Exception as e:
        logger.error(f"Error processing stream {stream_id}: {e}")

    # Close database connections after processing
    for conn in connections.all():
        conn.close()

    return success


class Command(BaseCommand):
    help = "Runs streams that are due for execution with improved reliability and performance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-retries",
            type=int,
            default=DEFAULT_MAX_RETRIES,
            help="Maximum number of retries for failed streams",
        )
        parser.add_argument(
            "--retry-delay",
            type=int,
            default=DEFAULT_RETRY_DELAY,
            help="Delay between retries in seconds",
        )
        parser.add_argument(
            "--processes",
            type=int,
            default=multiprocessing.cpu_count(),
            help="Number of processes to use for parallel execution",
        )

    def get_due_streams(self) -> List[Stream]:
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
            .order_by("next_run")
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

    def process_streams(
        self,
        streams: List[Stream],
        stats: StreamExecutionStats,
        max_retries: int,
        num_processes: int,
    ) -> None:
        """Process streams in parallel using multiprocessing."""
        if not streams:
            return

        # Close database connections before forking
        for conn in connections.all():
            conn.close()

        # Prepare arguments for multiprocessing - only pass IDs
        stream_args = [(stream.id, max_retries) for stream in streams]

        # Use multiprocessing Pool for parallel execution
        try:
            with multiprocessing.Pool(processes=num_processes) as pool:
                results = pool.starmap(process_single_stream, stream_args)

                # Update stats based on results
                succeeded = sum(1 for result in results if result)
                failed = sum(1 for result in results if not result)

                stats.streams_succeeded = succeeded
                stats.streams_failed = failed
                stats.save(update_fields=["streams_succeeded", "streams_failed"])

        except KeyboardInterrupt:
            logger.info("Gracefully shutting down worker processes...")
            pool.terminate()
            pool.join()
            raise

    def handle(self, *args, **options):
        self.stdout.write("Use celery!!!")

        # self.stdout.write("Starting one-time parallel stream execution...")
        # logger.info("Stream execution started")
        #
        # # Log timezone information
        # logger.info(f"Current timezone: {timezone.get_current_timezone_name()}")
        # logger.info(f"Current time: {timezone.now()}")
        #
        # # Reactivate any failed streams
        # Stream.reactivate_failed_streams() # failed to active
        # logger.info("Reactivated failed streams")
        #
        # max_retries = options["max_retries"]
        # num_processes = options["processes"]
        # logger.info(
        #     f"Configuration: max_retries={max_retries}, processes={num_processes}"
        # )
        #
        # try:
        #     # Create execution stats
        #     stats = StreamExecutionStats.objects.create()
        #     logger.info(f"Starting execution at {stats.execution_start}")
        #
        #     # Get all due streams
        #     due_streams = self.get_due_streams() # status = active & failed
        #
        #     if due_streams:
        #         # Update stats before processing
        #         stats.streams_attempted = len(due_streams)
        #         stats.save()
        #
        #         # Process all streams in parallel
        #         self.process_streams(due_streams, stats, max_retries, num_processes)
        #
        #         # Log final results
        #         total = stats.streamxs_succeeded + stats.streams_failed
        #         logger.info(
        #             f"Stream execution results:\n"
        #             f"Total streams processed: {stats.streams_attempted}\n"
        #             f"Successfully completed: {stats.streams_succeeded}\n"
        #             f"Failed: {stats.streams_failed}\n"
        #             f"Total processed: {total}"
        #         )
        #     else:
        #         logger.info("No due streams found")
        #
        #     # Update stats
        #     stats.execution_end = timezone.now()
        #     stats.save()
        #     stats.calculate_stats()
        #
        #     duration = stats.execution_end - stats.execution_start
        #     logger.info(
        #         f"Execution completed in {duration.total_seconds():.2f} seconds"
        #     )
        #
        # except Exception as e:
        #     logger.exception(f"Critical error in stream execution: {e}")
        #     raise
