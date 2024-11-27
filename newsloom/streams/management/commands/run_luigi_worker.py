from django.core.management.base import BaseCommand
import luigi
import logging
from streams.models import Stream, LuigiTaskLog
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
                            # Create task log entry
                            task_log = LuigiTaskLog.objects.create(
                                stream=stream,
                                task_id=str(task_instance.task_id),
                                status='RUNNING'
                            )
                            
                            try:
                                # Run the task
                                luigi.build([task_instance], local_scheduler=True)
                                # Update log on success
                                task_log.status = 'COMPLETED'
                                task_log.completed_at = timezone.now()
                                task_log.save()
                            except Exception as e:
                                # Update log on failure
                                task_log.status = 'FAILED'
                                task_log.completed_at = timezone.now()
                                task_log.error_message = str(e)
                                task_log.save()
                                raise  # Re-raise the exception for the outer try-except
                    except Exception as e:
                        logger.error(f"Error processing stream {stream.id}: {e}")
                
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(60)