import logging
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Dict, List
from urllib.parse import quote

from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from .playwright import USER_AGENTS, get_stream, save_links, update_stream_status

logger = logging.getLogger(__name__)

BING_SEARCH_URL = "https://www.bing.com/search"
BING_NEWS_URL = "https://www.bing.com/news/search"

# Add a thread-local storage for task cancellation
_local = threading.local()


def cancellable_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Initialize cancellation flag
        _local.cancelled = False
        try:
            return func(*args, **kwargs)
        finally:
            # Clean up
            if hasattr(_local, "cancelled"):
                del _local.cancelled

    return wrapper


def check_cancelled():
    """Check if the current task has been cancelled."""
    return getattr(_local, "cancelled", False)


@cancellable_task
def search_bing(
    stream_id: int,
    keywords: List[str],
    max_results_per_keyword: int = 5,
    search_type: str = "news",
    debug: bool = False,
) -> Dict:
    """
    Search Bing for articles matching the given keywords.

    Args:
        stream_id: ID of the stream
        keywords: List of keywords to search for
        max_results_per_keyword: Maximum number of results per keyword
        search_type: Type of search ('news' or 'web')
        debug: Debug mode flag
        # TODO: add location
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

        all_links = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not debug)
            selected_user_agent = random.choice(USER_AGENTS)
            context = browser.new_context(
                user_agent=selected_user_agent,
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            try:
                stealth_sync(page)

                for keyword in keywords:
                    # Check if task has been cancelled
                    if check_cancelled():
                        logger.info("Task cancelled, stopping execution")
                        break

                    # Add debug logging
                    if debug:
                        logger.info(f"Searching for keyword: {keyword}")
                        logger.info(f"Using user agent: {selected_user_agent}")

                    # Construct search query
                    query = quote(keyword)

                    # Choose appropriate URL and selectors based on search type
                    base_url = (
                        BING_NEWS_URL if search_type == "news" else BING_SEARCH_URL
                    )
                    search_url = f"{base_url}?q={query}"

                    # Add additional wait for news content
                    if search_type == "news":
                        page.wait_for_timeout(
                            5000
                        )  # Wait 5 seconds for dynamic content

                    # Update selector for news articles
                    if search_type == "news":
                        link_selector = "div.news-card a.title"
                    else:
                        link_selector = "h2 > a"

                    page.goto(search_url, timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=60000)

                    elements = page.query_selector_all(link_selector)

                    if debug:
                        logger.info(f"Total elements found: {len(elements)}")
                        # Log the page HTML for debugging
                        logger.info(f"Page HTML: {page.content()}")

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

                    # Add debug pause if needed
                    if debug:
                        logger.info("Waiting for manual inspection (30 seconds)...")
                        page.wait_for_timeout(30000)  # 30 second pause for debugging

            finally:
                browser.close()

        # Save links only if task wasn't cancelled
        if not check_cancelled():
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
