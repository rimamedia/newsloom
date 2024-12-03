import logging
import time
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand
from django.utils import timezone
from streams.scheduler import StreamScheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs the stream scheduler continuously"

    def handle(self, *args, **options):
        self.stdout.write("Starting stream scheduler...")
        logger.info("Stream scheduler started")

        # Create a thread pool
        with ThreadPoolExecutor(max_workers=10) as executor:
            while True:
                try:
                    # Execute due tasks in parallel
                    executor.submit(StreamScheduler.execute_due_tasks)

                    # Retry failed tasks in parallel
                    executor.submit(StreamScheduler.retry_failed_tasks)

                    logger.debug(f"Scheduler heartbeat at {timezone.now()}")
                    time.sleep(30)

                except Exception as e:
                    logger.exception(f"Error in stream scheduler: {e}")
                    time.sleep(5)
