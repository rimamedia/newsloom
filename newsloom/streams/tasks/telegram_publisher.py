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
        bot = Bot(token=bot_token)

        async def publish_messages():
            nonlocal result
            now = timezone.now()
            time_threshold = now - timezone.timedelta(minutes=time_window_minutes)

            news_items = await sync_to_async(list)(
                News.objects.filter(
                    source=stream.source, published_at__gte=time_threshold
                ).order_by("published_at")[:batch_size]
            )

            for news in news_items:
                try:
                    await bot.send_message(chat_id=channel_id, text=news.text)
                    result["published_count"] += 1
                    result["published_news_ids"].append(news.id)

                    TelegramPublishLog.objects.create(news=news, media=stream.media)

                except Exception as e:
                    logger.error(f"Failed to publish news {news.id}: {str(e)}")
                    result["failed_count"] += 1
                    result["failed_news_ids"].append(news.id)
                    result["errors"].append(str(e))

        loop = asyncio.get_event_loop()
        try:
            # Run the async function in the loop
            loop.run_until_complete(publish_messages())
        finally:
            try:
                # Clean up pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

                # Close the loop
                loop.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
                result["errors"].append(str(e))

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
