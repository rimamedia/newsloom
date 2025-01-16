import asyncio
import logging
from typing import Any, Dict

from crawl4ai import AsyncWebCrawler
from django.utils import timezone
from sources.models import News

logger = logging.getLogger(__name__)


async def _process_news_batch(news_items):
    """Process a batch of news items using crawl4ai."""
    async with AsyncWebCrawler() as crawler:
        for news in news_items:
            try:
                result = await crawler.arun(url=news.url)
                if result and result.markdown:
                    news.text = result.markdown
                    news.updated_at = timezone.now()
                    news.save(update_fields=["text", "updated_at"])
                    logger.info(f"Successfully scraped content for news {news.id}")
                else:
                    logger.warning(f"No content found for news {news.id}")
            except Exception as e:
                logger.error(f"Error scraping content for news {news.id}: {str(e)}")


def web_scraper(stream_id: int, batch_size: int = 10, **kwargs) -> Dict[str, Any]:
    """
    Task to scrape content for news articles with empty text.

    Args:
        stream_id: ID of the stream
        batch_size: Number of news articles to process in each batch
        **kwargs: Additional configuration parameters

    Returns:
        Dict containing task execution results
    """
    try:
        # Get news articles with empty text
        empty_news = News.objects.filter(text__isnull=True).order_by("-created_at")[
            :batch_size
        ]

        if not empty_news:
            logger.info("No empty news articles found to process")
            return {"status": "success", "processed": 0}

        # Process the batch
        asyncio.run(_process_news_batch(empty_news))

        return {
            "status": "success",
            "processed": len(empty_news),
        }

    except Exception as e:
        logger.error(f"Error in web_scraper task: {str(e)}")
        raise
