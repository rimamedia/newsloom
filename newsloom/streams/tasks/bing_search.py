import logging
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from urllib.parse import quote

from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from .playwright import USER_AGENTS, get_stream, save_links, update_stream_status

logger = logging.getLogger(__name__)

BING_SEARCH_URL = "https://www.bing.com/search"
BING_NEWS_URL = "https://www.bing.com/news/search"


def search_bing(
    stream_id: int,
    keywords: List[str],
    location: str = None,
    max_results_per_keyword: int = 5,
    search_type: str = "news",
) -> Dict:
    """
    Search Bing for articles matching the given keywords.

    Args:
        stream_id: ID of the stream
        keywords: List of keywords to search for
        location: Optional location to target
        max_results_per_keyword: Maximum number of results per keyword
        search_type: Type of search ('news' or 'web')
    """
    result = {
        "extracted_count": 0,
        "saved_count": 0,
        "links": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        # Get stream in a separate thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            stream_future = executor.submit(get_stream, stream_id)
            stream = stream_future.result()

        if not stream or not stream.source:
            raise ValueError("Stream or stream source not found")

        all_links = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            try:
                stealth_sync(page)

                for keyword in keywords:
                    # Construct search query
                    query = quote(keyword)
                    if location:
                        query = f"{query} location:{location}"

                    # Choose appropriate URL and selectors based on search type
                    base_url = (
                        BING_NEWS_URL if search_type == "news" else BING_SEARCH_URL
                    )
                    search_url = f"{base_url}?q={query}"

                    # Different selectors for news and web search
                    link_selector = (
                        "a.news-card-title" if search_type == "news" else "h2 > a"
                    )

                    page.goto(search_url, timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=60000)

                    # Extract links
                    elements = page.query_selector_all(link_selector)

                    for element in elements[:max_results_per_keyword]:
                        href = element.get_attribute("href")
                        title = element.text_content()

                        if href and not href.startswith("/"):
                            link_data = {
                                "url": href,
                                "title": title.strip() if title else None,
                                "keyword": keyword,
                            }
                            all_links.append(link_data)
                            result["links"].append(link_data)
                            result["extracted_count"] += 1
                            logger.info(
                                f"Found article for keyword '{keyword}': {href}"
                            )

            finally:
                browser.close()

        # Save links
        with ThreadPoolExecutor(max_workers=1) as executor:
            save_future = executor.submit(save_links, all_links, stream)
            result["saved_count"] = save_future.result()

        logger.info(
            f"Successfully extracted {result['extracted_count']} links "
            f"and saved {result['saved_count']} new links."
        )

        return result

    except Exception as e:
        logger.error(f"Error in Bing search: {str(e)}", exc_info=True)
        result["error"] = str(e)

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                update_stream_status,
                stream_id,
                status="failed",
                last_run=timezone.now(),
            )
        raise e
