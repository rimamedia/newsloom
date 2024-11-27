from django.utils import timezone
from .models import Stream

class StreamScheduler:
    """Manages the scheduling of Stream tasks"""
    
    @classmethod
    def schedule_pending_tasks(cls):
        """Schedule all pending tasks that are due to run"""
        pending_streams = Stream.objects.filter(
            status='active',
            next_run__lte=timezone.now()
        )
        
        for stream in pending_streams:
            try:
                stream.schedule_luigi_task()
            except Exception as e:
                print(f"Failed to schedule stream {stream.id}: {e}")

    @classmethod
    def reschedule_failed_tasks(cls):
        """Attempt to reschedule failed tasks"""
        failed_streams = Stream.objects.filter(status='failed')
        
        for stream in failed_streams:
            try:
                stream.schedule_luigi_task()
            except Exception as e:
                print(f"Failed to reschedule stream {stream.id}: {e}") 