from datetime import datetime

from django.utils import timezone
from duckduckgo_search import DDGS

from sources.dataclasses import Link


def search_duckduckgo(
    keywords: str,
    max_results: int | None = 10,
    region: str | None = "wt-wt",
    time_range: str | None = "d",  # 'd' for last 24 hours
    safesearch: str | None = "moderate",
) -> list[Link]:
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
    links = []
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
            if published_date:
                published_at = datetime.strptime(published_date, "%Y-%m-%d")
            else:
                published_at = timezone.now()
            links.append(Link(link=url, title=title, text=body, published_at=published_at))
    return links





