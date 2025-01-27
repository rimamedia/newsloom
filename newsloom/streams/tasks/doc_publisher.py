import asyncio
import logging

from asgiref.sync import sync_to_async
from django.utils import timezone
from sources.models import Doc
from streams.models import Stream, TelegramDocPublishLog
from telegram import Bot
from telegram.constants import ParseMode


def publish_docs(
    stream_id,
    channel_id,
    bot_token,
    batch_size=10,
    **kwargs,  # Accept any additional configuration parameters
):
    """
    Publish docs from database to Telegram channel.

    Args:
        stream_id (int): ID of the stream
        channel_id (str): Telegram channel ID
        bot_token (str): Telegram bot token
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

        async def publish_messages(bot, stream, channel_id, batch_size, result):
            # Get unpublished docs from media (new or failed status)
            docs = await sync_to_async(list)(
                Doc.objects.filter(
                    media=stream.media,
                    status__in=["new", "failed"],  # Process both new and failed docs
                ).order_by("created_at")[:batch_size]
            )

            for doc in docs:
                # Build message with title and text
                # Title in bold
                message = f"<b>{doc.title}</b>"
                if doc.text:
                    message += f"\n\n{doc.text}"
                if doc.link:
                    # Add link on new line
                    message += f"\n\n{doc.link}"

                # Add debug logging before sending
                logger.info(
                    f"Attempting to send message for doc {doc.id} to channel {channel_id}"
                )
                logger.debug(f"Message content: {message}")

                try:
                    # Try to send message to Telegram
                    await bot.send_message(
                        chat_id=channel_id, text=message, parse_mode=ParseMode.HTML
                    )
                    logger.info(f"Successfully sent message for doc {doc.id}")

                    # Message sent successfully, mark as published
                    result["published_count"] += 1
                    result["published_doc_ids"].append(doc.id)

                    # Update doc status to publish and set published timestamp
                    now = timezone.now()
                    try:
                        await sync_to_async(Doc.objects.filter(id=doc.id).update)(
                            status="publish", published_at=now
                        )
                        logger.info(f"Updated doc {doc.id} status to publish")
                    except Exception as update_error:
                        logger.error(
                            f"Failed to update doc {doc.id} status: {str(update_error)}"
                        )
                        # Don't raise the error, just log it

                    # Try to create publish log
                    try:
                        await sync_to_async(TelegramDocPublishLog.objects.create)(
                            doc=doc, media=stream.media
                        )
                        logger.info(f"Created publish log for doc {doc.id}")
                    except Exception as log_error:
                        logger.error(
                            f"Failed to create publish log for doc {doc.id}: {str(log_error)}"
                        )
                        # Don't raise the error, just log it

                    logger.info(f"Successfully published doc {doc.id}")

                except Exception as e:
                    # Only mark as failed if Telegram message sending fails
                    error_msg = f"Failed to publish doc {doc.id} to Telegram: {str(e)}"
                    logger.error(error_msg)
                    result["failed_count"] += 1
                    result["failed_doc_ids"].append(doc.id)
                    result["errors"].append(error_msg)

                    # Update doc status to failed only if message sending failed
                    await sync_to_async(Doc.objects.filter(id=doc.id).update)(
                        status="failed"
                    )

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                publish_messages(bot, stream, channel_id, batch_size, result)
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
        Stream.update_status(stream_id, status="failed")
        raise e

    return result
