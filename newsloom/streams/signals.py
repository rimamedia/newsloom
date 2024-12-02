from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Stream


@receiver(post_save, sender=Stream)
def handle_stream_save(sender, instance, created, **kwargs):
    """Handle stream creation and updates."""
    if created or instance.status == "active":
        # Set next_run time for new or active streams
        next_run = instance.get_next_run_time()
        if timezone.is_naive(next_run):
            next_run = timezone.make_aware(next_run)

        # Only update if the next_run time has changed
        if instance.next_run != next_run:
            instance.next_run = next_run
            instance.save(update_fields=["next_run"])
