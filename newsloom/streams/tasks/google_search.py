import logging
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Dict, List, Optional
from urllib.parse import quote

from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from .playwright import (
    BROWSER_OPTIONS,
    CONTEXT_OPTIONS,
    USER_AGENTS,
    get_stream,
    save_links,
    update_stream_status,
)

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.google.com/search"
GOOGLE_NEWS_URL = "https://news.google.com/search"

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
def search_google(
    stream_id: int,
    keywords: List[str],
    max_results_per_keyword: int = 5,
    days_ago: Optional[int] = None,
    search_type: str = "news",
    debug: bool = False,
) -> Dict:
    """
    Search Google for articles matching the given keywords.

    Args:
        stream_id: ID of the stream
        keywords: List of keywords to search for
        max_results_per_keyword: Maximum number of results per keyword
        days_ago: Filter results from the last X days
        search_type: Type of search ('news' or 'web')
        debug: Debug mode flag
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
            # Always use headless mode in container
            browser_options = {**BROWSER_OPTIONS}
            browser = p.chromium.launch(**browser_options)

            try:
                # Use optimized context options
                context_options = {
                    **CONTEXT_OPTIONS,
                    "user_agent": random.choice(USER_AGENTS),
                }
                context = browser.new_context(**context_options)

                try:
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
                                logger.info(
                                    f"Using user agent: {context_options['user_agent']}"
                                )

                            # Construct search query with time filter if specified
                            query = quote(keyword)
                            if days_ago:
                                query += f"+when:{days_ago}d"

                            # Choose appropriate URL and selectors based on search type
                            base_url = (
                                GOOGLE_NEWS_URL
                                if search_type == "news"
                                else GOOGLE_SEARCH_URL
                            )
                            search_url = f"{base_url}?q={query}"

                            # Add reduced wait for content
                            page.wait_for_timeout(2000)

                            # Update selector based on search type
                            if search_type == "news":
                                link_selector = "article a[href*='articles']"
                            else:
                                link_selector = "div.g a[href^='http']"

                            # Reduced timeouts and added wait_until option
                            page.goto(
                                search_url, timeout=30000, wait_until="domcontentloaded"
                            )
                            page.wait_for_load_state("networkidle", timeout=30000)

                            elements = page.query_selector_all(link_selector)

                            if debug:
                                logger.info(f"Total elements found: {len(elements)}")

                            for element in elements[:max_results_per_keyword]:
                                try:
                                    href = element.get_attribute("href")
                                    # Get text content without timeout
                                    title = element.evaluate("el => el.textContent")

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
                                except Exception as e:
                                    logger.warning(
                                        f"Error processing element: {str(e)}"
                                    )
                                    continue

                            # Reduced debug pause
                            if debug:
                                logger.info(
                                    "Waiting for manual inspection (10 seconds)..."
                                )
                                page.wait_for_timeout(10000)
                    finally:
                        if page:
                            page.close()
                finally:
                    if context:
                        context.close()
            finally:
                if browser:
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
        logger.error(f"Error in Google search: {str(e)}", exc_info=True)
        result["error"] = str(e)

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                update_stream_status,
                stream_id,
                status="failed",
                last_run=timezone.now(),
            )
        raise e
