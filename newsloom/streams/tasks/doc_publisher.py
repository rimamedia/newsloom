import asyncio
import logging
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.utils import timezone
from sources.models import Doc
from streams.models import Stream, TelegramPublishLog
from telegram import Bot


def publish_docs(
    stream_id,
    channel_id,
    bot_token,
    time_window_minutes=60,
    batch_size=10,
):
    """
    Publish docs from database to Telegram channel.

    Args:
        stream_id (int): ID of the stream
        channel_id (str): Telegram channel ID
        bot_token (str): Telegram bot token
        time_window_minutes (int): Time window in minutes to look back for docs in query
        batch_size (int): Maximum number of docs to process

    Returns:
        dict: Result containing processed counts and any errors
    """
    logger = logging.getLogger(__name__)
    result = {
        "published_count": 0,
        "failed_count": 0,
        "published_doc_ids": [],
        "failed_doc_ids": [],
        "errors": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        # Get stream and validate media
        stream = Stream.objects.get(id=stream_id)
        if not stream.media:
            raise ValueError("Stream must have an associated media")

        bot = Bot(token=bot_token)

        async def publish_messages(
            bot, stream, channel_id, time_threshold, batch_size, result
        ):
            # Get docs from media within time window
            docs = await sync_to_async(list)(
                Doc.objects.filter(
                    media=stream.media,
                    created_at__gte=time_threshold,
                    status="new",  # Only process new docs
                ).order_by("created_at")[:batch_size]
            )

            for doc in docs:
                try:
                    # Build message with title and text
                    message = f"{doc.title}"
                    if doc.text:
                        message += f"\n\n{doc.text[:250]}..."  # Truncate long text
                    if doc.link:
                        message += f"\n\n{doc.link}"

                    # Send message to Telegram
                    await bot.send_message(chat_id=channel_id, text=message)
                    result["published_count"] += 1
                    result["published_doc_ids"].append(doc.id)

                    # Update doc status to published
                    await sync_to_async(Doc.objects.filter(id=doc.id).update)(
                        status="published"
                    )

                    # Create publish log
                    await sync_to_async(TelegramPublishLog.objects.create)(
                        doc=doc, media=stream.media
                    )

                    logger.info(f"Successfully published doc {doc.id}")

                except Exception as e:
                    error_msg = f"Failed to publish doc {doc.id}: {str(e)}"
                    logger.error(error_msg)
                    result["failed_count"] += 1
                    result["failed_doc_ids"].append(doc.id)
                    result["errors"].append(error_msg)

                    # Update doc status to failed
                    await sync_to_async(Doc.objects.filter(id=doc.id).update)(
                        status="failed"
                    )

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Use time_window_minutes only for querying docs
            time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
            loop.run_until_complete(
                publish_messages(
                    bot, stream, channel_id, time_threshold, batch_size, result
                )
            )
        finally:
            loop.close()

        # Update stream status and timing
        now = timezone.now()
        stream.last_run = now
        stream.next_run = (
            stream.get_next_run_time()
        )  # Use stream's frequency for next run
        stream.save(update_fields=["last_run", "next_run"])

        logger.info(
            f"Published {result['published_count']} docs, "
            f"failed {result['failed_count']} docs"
        )

    except Exception as e:
        error_msg = f"Error in doc publisher task: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result["errors"].append(error_msg)
        Stream.objects.filter(id=stream_id).update(
            status="failed", last_run=timezone.now()
        )
        raise e

    return result
