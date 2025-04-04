import logging
import random
from urllib.parse import quote

from django.conf import settings
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from sources.dataclasses import Link

logger = logging.getLogger(__name__)

BING_SEARCH_URL = "https://www.bing.com/search"
BING_NEWS_URL = "https://www.bing.com/news/search"


def search_bing(
    keywords: list[str],
    max_results_per_keyword: int = 5,
    search_type: str = "news",
) -> list[Link]:
    """
    Search Bing for articles matching the given keywords from the last 24 hours.

    Args:
        keywords: List of keywords to search for
        max_results_per_keyword: Maximum number of results per keyword
        search_type: Type of search ('news' or 'web')
    """

    links = []

    with sync_playwright() as p:
        # Always use headless mode in container
        browser_options = {**settings.PLAYWRIGHT_BROWSER_OPTIONS}
        browser = p.chromium.launch(**browser_options)

        # Use optimized context options
        context_options = {
            **settings.PLAYWRIGHT_CONTEXT_OPTIONS,
            "user_agent": random.choice(settings.PLAYWRIGHT_USER_AGENTS),
        }
        context = browser.new_context(**context_options)
        page = context.new_page()
        stealth_sync(page)

        for keyword in keywords:

            # Construct search query
            query = quote(keyword)

            # Choose appropriate URL and selectors based on search type
            base_url = (
                BING_NEWS_URL
                if search_type == "news"
                else BING_SEARCH_URL
            )
            # Add time filter for last 24 hours (interval=1)
            time_filter = (
                "&qft=interval~%221%22" if search_type == "news" else ""
            )
            search_url = f"{base_url}?q={query}{time_filter}"

            # Add reduced wait for news content
            if search_type == "news":
                page.wait_for_timeout(2000)  # Reduced from 5s to 2s

            # Update selector for news articles
            if search_type == "news":
                link_selector = "div.news-card a.title"
            else:
                link_selector = "h2 > a"

            # Reduced timeouts and added wait_until option
            page.goto(
                search_url, timeout=30000, wait_until="domcontentloaded"
            )
            page.wait_for_load_state("networkidle", timeout=30000)

            elements = page.query_selector_all(link_selector)

            for element in elements[:max_results_per_keyword]:

                href = element.get_attribute("href")
                # Get text content without timeout
                title = element.evaluate("el => el.textContent")

                if href and not href.startswith("/"):
                    links.append(Link(link=href, title=title.strip() if title else None))

            page.wait_for_timeout(10000)  # Reduced from 30s to 10s

    return links