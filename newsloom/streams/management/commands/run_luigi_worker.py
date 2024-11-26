from django.core.management.base import BaseCommand
import luigi
import logging
from streams.models import Stream
from django.utils import timezone
import time

class Command(BaseCommand):
    help = 'Runs the Luigi worker to process streams'

    def handle(self, *args, **options):
        logger = logging.getLogger(__name__)
        
        while True:
            try:
                # Get all active streams that need to run
                pending_streams = Stream.objects.filter(
                    status='active',
                    next_run__lte=timezone.now()
                )
                
                for stream in pending_streams:
                    try:
                        # Get task instance
                        task_instance = stream.schedule_luigi_task()
                        if task_instance:
                            # Run the task
                            luigi.build([task_instance], local_scheduler=True)
                    except Exception as e:
                        logger.error(f"Error processing stream {stream.id}: {e}")
                
                # Sleep for a short period
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(60)  # Wait before retrying 