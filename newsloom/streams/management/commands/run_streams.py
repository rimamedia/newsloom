import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone
from streams.scheduler import StreamScheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs the stream scheduler continuously"

    def handle(self, *args, **options):
        self.stdout.write("Starting stream scheduler...")
        logger.info("Stream scheduler started")

        while True:
            try:
                # Execute due tasks
                StreamScheduler.execute_due_tasks()

                # Retry failed tasks
                StreamScheduler.retry_failed_tasks()

                # Log heartbeat
                logger.debug(f"Scheduler heartbeat at {timezone.now()}")

                # Sleep for a short interval (e.g., 30 seconds)
                time.sleep(30)

            except Exception as e:
                logger.exception(f"Error in stream scheduler: {e}")
                # Sleep for a short while before retrying
                time.sleep(5)
