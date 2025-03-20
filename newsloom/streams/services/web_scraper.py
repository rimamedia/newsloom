import asyncio
import logging
from typing import Any, Dict

from asgiref.sync import sync_to_async
from crawl4ai import AsyncWebCrawler
from django.utils import timezone
from sources.models import News

logger = logging.getLogger(__name__)


def _save_news(news, text, title=None):
    """Save news text and title in the database."""
    news.text = text
    if title:
        news.title = title
    news.updated_at = timezone.now()
    update_fields = ["text", "updated_at"]
    if title:
        update_fields.append("title")
    news.save(update_fields=update_fields)


async def _process_news_batch(news_items):
    """Process a batch of news items using crawl4ai to extract content."""
    async with AsyncWebCrawler() as crawler:
        for news in news_items:
            try:
                result = await crawler.arun(url=news.link)
                if result:
                    if result.markdown:
                        title = (
                            result.metadata.get("title") if result.metadata else None
                        )
                        await sync_to_async(_save_news)(news, result.markdown, title)
                        logger.info(f"Successfully scraped content for news {news.id}")
                else:
                    logger.warning(f"No content found for news {news.id}")
            except Exception as e:
                logger.error(f"Error scraping content for news {news.id}: {str(e)}")


async def _async_web_scraper(
    stream_id: int, batch_size: int = 10, **kwargs
) -> Dict[str, Any]:
    """Async implementation of web scraper task."""
    try:
        # Get news articles with empty text
        get_empty_news = sync_to_async(
            lambda: list(
                News.objects.filter(text__isnull=True).order_by("-created_at")[
                    :batch_size
                ]
            )
        )
        empty_news = await get_empty_news()

        if not empty_news:
            logger.info("No empty news articles found to process")
            return {"status": "success", "processed": 0}

        # Process the batch
        await _process_news_batch(empty_news)

        return {
            "status": "success",
            "processed": len(empty_news),
        }

    except Exception as e:
        logger.error(f"Error in web_scraper task: {str(e)}")
        raise


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
    return asyncio.run(_async_web_scraper(stream_id, batch_size, **kwargs))
