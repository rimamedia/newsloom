import logging
from datetime import datetime
from typing import Dict, List, Optional

from duckduckgo_search import DDGS
from sources.models import News
from streams.models import Stream

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
        # Get stream and its associated source first
        stream = Stream.objects.get(id=stream_id)
        if not stream.source:
            logger.error(f"No source found for stream {stream_id}")
            return {
                "total_results": 0,
                "new_articles": 0,
                "results": [],
                "error": "No source found for stream",
            }

        with DDGS() as ddgs:
            search_results = ddgs.news(
                keywords,
                region=region,
                safesearch=safesearch,
                timelimit=time_range,
                max_results=max_results,
            )

            for result in search_results:

                url = result.get("url")
                title = result.get("title")
                body = result.get("body")
                published_date = result.get("date")

                # Skip if required fields are missing
                if not all([title, url]):
                    continue

                # Create news article with correct fields and stream's source
                news_data = {
                    "title": title,
                    "link": url,
                    "text": body,  # Using 'text' instead of 'description'
                    "source": stream.source,  # Using stream's source
                    "published_at": (
                        datetime.fromisoformat(published_date.replace("Z", "+00:00"))
                        if published_date
                        else datetime.now()
                    ),
                }

                # Create or update news article
                news, created = News.objects.get_or_create(link=url, defaults=news_data)

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
