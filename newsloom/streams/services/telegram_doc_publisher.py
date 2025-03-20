import logging
import time
from typing import Dict

from django.utils import timezone
from sources.models import Doc
from streams.models import Stream, TelegramDocPublishLog

logger = logging.getLogger(__name__)


def telegram_doc_publisher(
    stream_id: int,
    message_template: str = "{title}\n\n{google_doc_link}",
    batch_size: int = 10,
    delay_between_messages: int = 2,
) -> Dict:
    """Publish Google Doc links to Telegram channel."""
    from streams.tasks.telegram import send_telegram_message

    stream = Stream.objects.get(id=stream_id)

    if not stream.media or not stream.media.telegram_chat_id:
        raise ValueError("Stream media must have a telegram_chat_id configured")

    # Get docs ready for publishing (status='edit' and has google_doc_link)
    docs = (
        Doc.objects.filter(
            status="edit", media=stream.media, google_doc_link__isnull=False
        )
        .exclude(
            id__in=TelegramDocPublishLog.objects.filter(media=stream.media).values_list(
                "doc_id", flat=True
            )
        )
        .order_by("created_at")[:batch_size]
    )

    if not docs.exists():
        return {"message": "No docs to publish"}

    processed = 0
    failed = 0

    for doc in docs:
        try:
            # Format message using template
            message = message_template.format(
                title=doc.title or "Untitled", google_doc_link=doc.google_doc_link
            )

            # Send to Telegram
            send_telegram_message(
                chat_id=stream.media.telegram_chat_id, message=message
            )

            # Log the publication
            TelegramDocPublishLog.objects.create(doc=doc, media=stream.media)

            # Update doc status and set published timestamp
            doc.status = "publish"  # Using correct status from Doc.STATUS_CHOICES
            doc.published_at = timezone.now()
            doc.save(update_fields=["status", "published_at"])

            processed += 1

            # Add delay between messages to avoid rate limiting
            if processed < len(docs):  # Don't delay after the last message
                time.sleep(delay_between_messages)

        except Exception as e:
            logger.error(f"Failed to publish doc {doc.id}: {e}")
            doc.status = "failed"
            doc.save(update_fields=["status"])
            failed += 1

    return {"processed": processed, "failed": failed, "total": len(docs)}
