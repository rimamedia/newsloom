import logging
from datetime import datetime
from typing import Dict, List, Optional

from duckduckgo_search import DDGS
from sources.models import News

logger = logging.getLogger(__name__)


def duckduckgo_search(
    stream_id: int,
    keywords: str,
    max_results: Optional[int] = 10,
    region: Optional[str] = "wt-wt",
    time_range: Optional[str] = "d",  # 'd' for last 24 hours
    safesearch: Optional[str] = "moderate",
) -> Dict:
    """
    Search for news articles using DuckDuckGo.

    Args:
        stream_id: ID of the stream
        keywords: Search query
        max_results: Maximum number of results to return (1-100)
        region: Region for search results (e.g., us-en, uk-en, wt-wt)
        time_range: Time range for results (d: day, w: week, m: month, y: year)
        safesearch: SafeSearch setting (on, moderate, off)

    Returns:
        Dict containing results summary
    """
    logger.info(
        f"Starting DuckDuckGo search for stream {stream_id} with time_range={time_range}"
    )

    created_count = 0
    results: List[Dict] = []

    try:
        with DDGS() as ddgs:
            search_results = ddgs.news(
                keywords,
                region=region,
                safesearch=safesearch,
                timelimit=time_range,
                max_results=max_results,
            )

            for result in search_results:
                # Create News object for each result
                news_data = {
                    "title": result.get("title"),
                    "link": result.get("url"),
                    "description": result.get("body"),
                    "published_at": datetime.fromisoformat(
                        result.get("date").replace("Z", "+00:00")
                    ),
                    "source_name": result.get("source"),
                    "stream_id": stream_id,
                }

                # Skip if required fields are missing
                if not all([news_data["title"], news_data["link"]]):
                    continue

                # Create or update news article
                news, created = News.objects.get_or_create(
                    link=news_data["link"], defaults=news_data
                )

                if created:
                    created_count += 1

                results.append(
                    {"title": news.title, "url": news.link, "created": created}
                )

        logger.info(
            f"DuckDuckGo search completed for stream {stream_id}. "
            f"Created {created_count} new articles."
        )

        return {
            "total_results": len(results),
            "new_articles": created_count,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error in DuckDuckGo search for stream {stream_id}: {str(e)}")
        raise
