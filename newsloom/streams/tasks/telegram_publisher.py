import asyncio
import logging

from asgiref.sync import sync_to_async
from django.utils import timezone
from sources.models import News
from streams.models import Stream, TelegramPublishLog
from telegram import Bot


def publish_to_telegram(
    stream_id, channel_id, bot_token, batch_size=10, time_window_minutes=10
):
    logger = logging.getLogger(__name__)
    result = {
        "published_count": 0,
        "failed_count": 0,
        "published_news_ids": [],
        "failed_news_ids": [],
        "errors": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        stream = Stream.objects.get(id=stream_id)
        if not stream.media:
            raise ValueError("Stream must have an associated media")

        bot = Bot(token=bot_token)

        async def publish_messages(
            bot, stream, channel_id, time_threshold, batch_size, result
        ):
            # Get all sources associated with the media
            media_sources = await sync_to_async(list)(stream.media.sources.all())

            # Get news from all media sources within time window
            news_items = await sync_to_async(list)(
                News.objects.filter(
                    source__in=media_sources,
                    link__isnull=False,
                    created_at__gte=time_threshold,
                ).order_by("created_at")[:batch_size]
            )

            for news in news_items:
                try:
                    # Build message with title and optional text
                    message = f"{news.title}"
                    if news.text:
                        message += f"\n\n{news.text[:250]}..."  # Truncate long text
                    message += f"\n\n{news.link}"

                    await bot.send_message(chat_id=channel_id, text=message)
                    result["published_count"] += 1
                    result["published_news_ids"].append(news.id)

                    # Create publish log
                    await sync_to_async(TelegramPublishLog.objects.create)(
                        news=news, media=stream.media
                    )

                except Exception as e:
                    logger.error(f"Failed to publish news {news.id}: {str(e)}")
                    result["failed_count"] += 1
                    result["failed_news_ids"].append(news.id)
                    result["errors"].append(str(e))

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            time_threshold = timezone.now() - timezone.timedelta(
                minutes=time_window_minutes
            )
            loop.run_until_complete(
                publish_messages(
                    bot, stream, channel_id, time_threshold, batch_size, result
                )
            )
        finally:
            loop.close()

        # Update stream status
        stream.last_run = timezone.now()
        stream.save(update_fields=["last_run"])

    except Exception as e:
        logger.error(f"Error publishing to Telegram: {str(e)}", exc_info=True)
        result["errors"].append(str(e))
        Stream.objects.filter(id=stream_id).update(
            status="failed", last_run=timezone.now()
        )
        raise e

    return result
