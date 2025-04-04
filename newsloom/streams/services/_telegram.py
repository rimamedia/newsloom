import time

from django.db.models import QuerySet
from django.utils import timezone
from sources.models import News, Doc
from streams.models import Stream, TelegramPublishLog, TelegramDocPublishLog
from mediamanager.models import Media

from newsloom.contrib.telegramm import send_message_to_telegram


def send_news_to_telegram(channel_id: str, bot_token: str, list_of_news: QuerySet[News], media: Media | None) -> None:
    for news in list_of_news:
        # Build message with title and optional text
        message = f"{news.title}"
        if news.text:
            message += f"\n\n{news.text[:250]}..."  # Truncate long text
        message += f"\n\n{news.link}"

        send_message_to_telegram(bot_token, channel_id, message)
        TelegramPublishLog.objects.get_or_create(news=news, media=media)



def telegram_doc_publisher(
    stream: Stream,
    message_template: str = "{title}\n\n{google_doc_link}",
    batch_size: int = 10,
    delay_between_messages: int = 2,
) -> None:
    """Publish Google Doc links to Telegram channel."""
    # from streams.tasks.telegram import send_telegram_message


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

    processed  = 0
    for doc in docs:
        # Format message using template
        message = message_template.format(title=doc.title or "Untitled", google_doc_link=doc.google_doc_link)
        # Send to Telegram
        send_message_to_telegram('', stream.media.telegram_chat_id, message)

        # Log the publication
        TelegramDocPublishLog.objects.get_or_create(doc=doc, media=stream.media)

        # Update doc status and set published timestamp
        doc.status = "publish"  # Using correct status from Doc.STATUS_CHOICES
        doc.published_at = timezone.now()
        doc.save(update_fields=["status", "published_at"])

        processed += 1

        # Add delay between messages to avoid rate limiting
        if processed < len(docs):  # Don't delay after the last message
            time.sleep(delay_between_messages)
