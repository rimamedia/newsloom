import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Stream

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Stream)
def handle_stream_save(sender, instance, created, **kwargs):
    """Handle stream creation and updates."""
    try:
        # Skip if this is an update of last_run or next_run fields
        if not created and kwargs.get("update_fields") in [
            {"next_run"},
            {"last_run", "next_run"},
        ]:
            return

        # Calculate next run only for new streams or status changes to active
        if created or (
            "status" in (kwargs.get("update_fields") or [])
            and instance.status == "active"
        ):
            next_run = instance.get_next_run_time()
            if timezone.is_naive(next_run):
                next_run = timezone.make_aware(next_run)

            if instance.next_run != next_run:
                with transaction.atomic():
                    Stream.objects.filter(id=instance.id).update(next_run=next_run)

    except Exception as e:
        logger.error(f"Error in stream signal handler: {e}")
