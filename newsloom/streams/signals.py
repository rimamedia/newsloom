from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Stream
from .scheduler import StreamScheduler

@receiver(post_save, sender=Stream)
def handle_stream_save(sender, instance, created, **kwargs):
    """Handle stream creation and updates"""
    if created:
        # New stream - just set the next_run time
        instance.next_run = instance.get_next_run_time()
        instance.save(update_fields=['next_run'])
    else:
        # Existing stream - only schedule if active
        if instance.status == 'active':
            try:
                instance.schedule_luigi_task()
            except Exception as e:
                print(f"Failed to update stream {instance.id} schedule: {e}") 