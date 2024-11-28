import asyncio
import logging

import luigi
from asgiref.sync import sync_to_async
from django.utils import timezone
from sources.models import News
from streams.models import TelegramPublishLog
from telegram import Bot


class TelegramPublishingTask(luigi.Task):
    stream_id = luigi.IntParameter()
    scheduled_time = luigi.Parameter()
    channel_id = luigi.Parameter()
    bot_token = luigi.Parameter()
    batch_size = luigi.IntParameter(default=10)
    time_window_minutes = luigi.IntParameter(default=10)

    def run(self):
        from streams.models import Stream

        logger = logging.getLogger(__name__)

        try:
            # Get all necessary data synchronously first
            stream = Stream.objects.get(id=self.stream_id)
            media = stream.media

            if not media:
                raise ValueError("No media configured for this stream")

            # Get unpublished news synchronously
            published_news_ids = TelegramPublishLog.objects.filter(
                media=media
            ).values_list("news_id", flat=True)

            time_window = timezone.now() - timezone.timedelta(
                minutes=self.time_window_minutes
            )
            unpublished_news = list(
                News.objects.filter(
                    source__in=media.sources.all(), created_at__gte=time_window
                )
                .exclude(id__in=published_news_ids)
                .order_by("created_at")[: self.batch_size]
            )

            if not unpublished_news:
                logger.info("No unpublished news found")
                return

            # Create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def publish_messages():
                bot = None
                try:
                    bot = Bot(token=self.bot_token)
                    # Verify channel access
                    await bot.get_chat(self.channel_id)

                    for news in unpublished_news:
                        try:
                            message = f"📰 {news.title if hasattr(news, 'title') else 'New article'}\n\n{news.link}"  # noqa: E501
                            await bot.send_message(
                                chat_id=self.channel_id,
                                text=message,
                                disable_web_page_preview=False,
                            )

                            # Create log entry synchronously
                            @sync_to_async
                            def create_log(news_item=news):
                                TelegramPublishLog.objects.create(
                                    news=news_item, media=media
                                )

                            await create_log()

                            logger.info(f"Published {news.link} to {self.channel_id}")
                            await asyncio.sleep(0.1)  # Small delay between messages

                        except Exception as e:
                            logger.error(f"Failed to publish news {news.id}: {str(e)}")
                            continue

                except Exception as e:
                    logger.error(f"Error in publish_messages: {str(e)}")
                    raise e
                finally:
                    if bot:
                        try:
                            await bot.close()
                        except Exception as e:
                            logger.error(f"Error closing bot: {str(e)}")

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

            # Update stream status synchronously
            stream.last_run = timezone.now()
            stream.save(update_fields=["last_run"])

        except Exception as e:
            logger.error(f"Error publishing to Telegram: {str(e)}", exc_info=True)
            Stream.objects.filter(id=self.stream_id).update(
                status="failed", last_run=timezone.now()
            )
            raise e

    def output(self):
        return luigi.LocalTarget(
            f"logs/telegram_publishing_{self.stream_id}_{self.scheduled_time}.txt"
        )
