from django.utils import timezone
from sources.models import Doc
from streams.models import Stream, TelegramDocPublishLog
from newsloom.contrib.telegramm import send_message_to_telegram


def publish_docs(
    stream: Stream,
    channel_id: str,
    bot_token: str,
    batch_size: int = 10,
    google_doc_links: bool = False,
    **kwargs,  # Accept any additional configuration parameters
):
    """
    Publish docs from database to Telegram channel.

    Args:
        stream (Stream): Stream
        channel_id (str): Telegram channel ID
        bot_token (str): Telegram bot token
        batch_size (int): Maximum number of docs to process
        google_doc_links (bool): Whether to include Google Doc links in messages
        **kwargs: Additional configuration parameters

    """

    if not stream.media:
        raise ValueError("Stream must have an associated media")
    docs = Doc.objects.filter(
            media=stream.media,
            status__in=[
                "new",
                "failed",
                "edit",
            ],  # Process both new and failed docs
        ).order_by("created_at")[:batch_size]

    for doc in docs:
        # Build message with title and text
        # Title in bold
        message = f"<b>{doc.title}</b>"
        if doc.text:
            message += f"\n\n{doc.text}"
        if doc.link:
            # Add link on new line
            message += f"\n\n{doc.link}"

        # Add Google Doc link if enabled in config
        if google_doc_links and doc.google_doc_link:
            message += f"\n\nGoogle Doc: {doc.google_doc_link}"

        send_message_to_telegram(bot_token, channel_id, message)

        Doc.objects.filter(id=doc.id).update( status="publish", published_at=timezone.now())
        TelegramDocPublishLog.objects.create(doc = doc, media = stream.media)
