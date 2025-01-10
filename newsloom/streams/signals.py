import logging

from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Stream

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Stream)
def handle_stream_save(sender, instance, created, **kwargs):
    """Handle stream creation and updates."""
    try:
        update_fields = kwargs.get("update_fields", set())

        # Skip if this is just a timing update
        if not created and update_fields in [{"next_run"}, {"last_run", "next_run"}]:
            return

        # Handle immediate setting updates
        if not created:
            # For status changes
            if "status" in update_fields or not update_fields:
                if instance.status == "active":
                    next_run = instance.get_next_run_time()
                    if timezone.is_naive(next_run):
                        next_run = timezone.make_aware(next_run)

                    if instance.next_run != next_run:
                        with transaction.atomic():
                            Stream.objects.filter(id=instance.id).update(
                                next_run=next_run,
                                version=models.F("version"),  # Increment version safely
                            )

            # For configuration or frequency changes
            if (
                "configuration" in update_fields
                or "frequency" in update_fields
                or not update_fields
            ):
                # Recalculate next run time
                next_run = instance.get_next_run_time()
                if timezone.is_naive(next_run):
                    next_run = timezone.make_aware(next_run)

                with transaction.atomic():
                    Stream.objects.filter(id=instance.id).update(
                        next_run=next_run,
                        version=models.F("version"),  # Increment version safely
                    )

        # For new streams
        elif created:
            next_run = instance.get_next_run_time()
            if timezone.is_naive(next_run):
                next_run = timezone.make_aware(next_run)

            with transaction.atomic():
                Stream.objects.filter(id=instance.id).update(next_run=next_run)

    except Exception as e:
        logger.error(f"Error in stream signal handler: {e}", exc_info=True)
