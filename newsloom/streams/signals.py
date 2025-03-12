from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Stream
from .services import get_periodic_task_by_stream, stream_to_periodic_task


@receiver(post_save, sender=Stream)
def post_save_stream(sender, instance, created, **kwargs):
    stream_to_periodic_task(instance)


@receiver(post_delete, sender=Stream)
def post_delete_stream(sender, instance, **kwargs):
    periodic_task = get_periodic_task_by_stream(instance)
    if periodic_task:
       periodic_task.delete()
