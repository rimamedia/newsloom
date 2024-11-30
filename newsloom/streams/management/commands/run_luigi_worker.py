import logging
import time

import luigi
from django.core.management.base import BaseCommand
from django.utils import timezone
from streams.models import LuigiTaskLog, Stream


class Command(BaseCommand):
    help = "Runs the Luigi worker to process streams"

    def process_streams(self, streams):
        logger = logging.getLogger(__name__)
        try:
            # Create task instances for all streams
            task_instances = []
            task_logs = {}

            for stream in streams:
                task_instance = stream.schedule_luigi_task()
                if task_instance:
                    # Create task log entry
                    task_log = LuigiTaskLog.objects.create(
                        stream=stream,
                        task_id=str(task_instance.task_id),
                        status="RUNNING",
                    )
                    task_logs[task_instance.task_id] = task_log
                    task_instances.append(task_instance)

            if task_instances:
                # Run all tasks in parallel using Luigi's built-in parallel execution
                luigi.build(task_instances, local_scheduler=True, workers=4)

                # Process outputs
                for task_instance in task_instances:
                    task_log = task_logs[task_instance.task_id]
                    try:
                        with task_instance.output().open("r") as f:
                            output_data = f.read()
                    except OSError as e:
                        output_data = None
                        logger.debug(f"Could not read task output: {e}")

                    task_log.status = "COMPLETED"
                    task_log.completed_at = timezone.now()
                    task_log.output_data = output_data
                    task_log.save()

        except Exception as e:
            logger.error(f"Error processing streams: {e}")
            # Mark all running tasks as failed
            for task_log in task_logs.values():
                if task_log.status == "RUNNING":
                    task_log.status = "FAILED"
                    task_log.completed_at = timezone.now()
                    task_log.error_message = str(e)
                    task_log.output_data = {"error": str(e)}
                    task_log.save()

    def handle(self, *args, **options):
        logger = logging.getLogger(__name__)

        while True:
            try:
                # Get all active streams that need to run
                pending_streams = Stream.objects.filter(
                    status="active", next_run__lte=timezone.now()
                )

                if pending_streams.exists():
                    self.process_streams(pending_streams)

                time.sleep(60)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(60)
