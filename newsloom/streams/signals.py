from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Stream


@receiver(post_save, sender=Stream)
def handle_stream_save(sender, instance, created, **kwargs):
    """Handle stream creation and updates."""
    try:
        # Only skip if this is a recursive update of next_run field
        if not created and kwargs.get("update_fields") == {"next_run"}:
            return

        # Calculate next run for new streams or active streams
        if created or instance.status == "active":
            next_run = instance.get_next_run_time()
            if timezone.is_naive(next_run):
                next_run = timezone.make_aware(next_run)

            # Only update if the next_run time has changed
            if instance.next_run != next_run:
                with transaction.atomic():
                    Stream.objects.filter(id=instance.id).update(next_run=next_run)
    except Exception as e:
        # Log the error but don't raise it to prevent cascading failures
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error in stream signal handler: {e}")
