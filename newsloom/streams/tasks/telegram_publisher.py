import luigi
import logging
from telethon import TelegramClient
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from sources.models import News
from streams.models import TelegramPublishLog
from django.db import transaction

class TelegramPublishingTask(luigi.Task):
    """Task for publishing news links to Telegram channels"""
    
    stream_id = luigi.IntParameter(description="ID of the Stream model instance")
    scheduled_time = luigi.Parameter(description="Scheduled execution time")
    batch_size = luigi.IntParameter(default=10, description="Maximum number of links to publish per run")
    
    def run(self):
        from streams.models import Stream
        
        logger = logging.getLogger(__name__)
        
        try:
            stream = Stream.objects.get(id=self.stream_id)
            media = stream.media
            
            if not media:
                raise ValueError("No media configured for this stream")
            
            # Get unpublished news by checking against TelegramPublishLog
            published_news_ids = TelegramPublishLog.objects.filter(
                media=media
            ).values_list('news_id', flat=True)
            
            unpublished_news = News.objects.filter(
                source__in=media.sources.all()
            ).exclude(
                id__in=published_news_ids
            ).order_by('published_at')[:self.batch_size]
            
            if not unpublished_news:
                logger.info("No unpublished news found")
                return
            
            # Initialize Telegram client
            client = TelegramClient(
                'news_publisher',
                settings.TELEGRAM_API_ID,
                settings.TELEGRAM_API_HASH
            )
            
            async def publish_messages():
                async with client:
                    channel = await client.get_entity(stream.configuration['channel_name'])
                    
                    for news in unpublished_news:
                        message = f"📰 {news.title if hasattr(news, 'title') else 'New article'}\n\n{news.link}"
                        await client.send_message(channel, message)
                        
                        # Log the publication
                        with transaction.atomic():
                            TelegramPublishLog.objects.create(
                                news=news,
                                media=media
                            )
                        
                        logger.info(f"Published {news.link} to {stream.configuration['channel_name']}")
            
            # Run the async function
            import asyncio
            asyncio.run(publish_messages())
            
            # Update stream status
            stream.last_run = timezone.now()
            stream.save(update_fields=['last_run'])
            
        except Exception as e:
            logger.error(f"Error publishing to Telegram: {str(e)}", exc_info=True)
            Stream.objects.filter(id=self.stream_id).update(
                status='failed',
                last_run=timezone.now()
            )
            raise e

    def output(self):
        return luigi.LocalTarget(f'/tmp/telegram_publish_{self.stream_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}') 