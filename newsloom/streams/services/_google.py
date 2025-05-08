import base64
import json
import logging
import random
from typing import Optional
from urllib.parse import quote, urlparse

from django.conf import settings
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_sync

from sources.dataclasses import Link

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.google.com/search"
GOOGLE_NEWS_URL = "https://news.google.com/search"


def decode_jslog(jslog_value: str) -> Optional[str]:
    """
    Decode Google jslog attribute to extract original URL
    """
    if not jslog_value:
        return None

    parts = jslog_value.split(';')

    # Find the part that contains Base64 data
    base64_part = None
    for part in parts:
        if ':' in part and part.strip().split(':')[0].isdigit():
            base64_part = part.strip().split(':', 1)[1].strip()
            break

    if not base64_part:
        return None

    try:
        # Decode the Base64 string
        decoded_bytes = base64.b64decode(base64_part)
        decoded_str = decoded_bytes.decode('utf-8')

        # The decoded string often contains a JSON-like array structure
        # Try to parse it as JSON if it starts with "[" and ends with "]"
        if decoded_str.startswith('[') and decoded_str.endswith(']'):
            try:
                json_data = json.loads(decoded_str)

                for item in json_data:
                    if isinstance(item, str) and (item.startswith('http://') or item.startswith('https://')):
                        return item

                return json_data
            except json.JSONDecodeError:
                return decoded_str

        return decoded_str
    except Exception as e:
        logger.error(f"Error decoding jslog_value={jslog_value} jslog: {e} ")
        return None


def is_url(string):
    if not string.startswith(('http://', 'https://')):
        string = 'http://' + string

    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def search_google(
        keywords: list[str],
        max_results_per_keyword: int = 5,
        days_ago: int | None = None,
        search_type: str = "news",
        **_kwargs
) -> list[Link]:
    """
    Search Google for articles matching the given keywords.

    Args:
        keywords: List of keywords to search for
        max_results_per_keyword: Maximum number of results per keyword
        days_ago: Filter results from the last X days
        search_type: Type of search ('news' or 'web')
    """
    links = []
    with sync_playwright() as p:
        # Always use headless mode in container
        browser = p.chromium.launch(**settings.PLAYWRIGHT_BROWSER_OPTIONS)
        context_options = {
            **settings.PLAYWRIGHT_CONTEXT_OPTIONS,
            "user_agent": random.choice(settings.PLAYWRIGHT_USER_AGENTS),
        }
        context = browser.new_context(**context_options)
        page = context.new_page()
        stealth_sync(page)

        for keyword in keywords:
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

            # Update selector and extraction logic based on search type
            if search_type == "news":
                # Target article headlines in Google News
                # Using multiple possible selectors for better reliability
                link_selectors = [
                    "article",  # News Elements
                    ".IFHyqb.DeXSAc.stiNJd",  # Alternative class-based selector
                ]

                # Navigate with longer timeout and wait for load
                page.goto(search_url, timeout=60000)

                # Try multiple selectors with reduced timeout
                link_selector = None
                for selector in link_selectors:
                    # Reduced timeout for each attempt
                    try:
                        element = page.wait_for_selector(selector, timeout=10000)
                    except PlaywrightTimeoutError:
                        continue

                    if element:
                        link_selector = selector
                        break

                if not link_selector:
                    raise Exception(
                        "No valid selector found for Google News articles"
                    )

                # Wait for network to be idle
                page.wait_for_load_state("networkidle", timeout=10000)
            else:
                link_selector = (
                    "div.g a[href^='http']"  # Regular search results
                )
                page.goto(
                    search_url,
                    timeout=60000,
                    wait_until="domcontentloaded",
                )
                page.wait_for_load_state("networkidle", timeout=10000)

            # Get all matching elements with error handling
            elements = page.query_selector_all(link_selector) or []

            # Process found elements
            for element in elements[:max_results_per_keyword]:
                # Get text content without timeout
                # Get title from the element itself for news articles
                title = None
                a_element = element.query_selector("a[href][tabindex='0']")
                if a_element and a_element.inner_text():
                    title = a_element.inner_text()
                if not title:
                    title = element.evaluate("el => el.textContent")
                if not title:
                    title = element.inner_text()

                # Get news href
                # Get original link, but there may be an error
                #  because this is jslog format from google
                href = element.get_attribute("href")
                jslog_element = element.query_selector("a[jslog]")
                if jslog_element:
                    _url = decode_jslog(jslog_element.get_attribute('jslog'))
                    if is_url(_url):
                        href = _url
                # get base href for a tag
                a_href_element = element.query_selector("div>div>a").get_attribute('href')
                if not a_href_element:
                    href = element.get_attribute('href')

                if href:
                    # Handle Google News article URLs
                    if search_type == "news":
                        if href.startswith("./"):
                            # Remove ./ prefix
                            href = href[2:]
                        if href.startswith("/"):
                            # Remove leading slash
                            href = href[1:]
                        # Ensure proper URL construction
                        if not href.startswith(
                                ("http://", "https://")
                        ):
                            href = f"https://news.google.com/{href}"
                    elif href.startswith("//"):
                        href = f"https:{href}"

                    if not href.startswith(("http://", "https://")):
                        logger.warning(
                            f"Skipping invalid URL: {href}"
                        )
                        continue

                    # Clean up Google News redirect URLs
                    if "news.google.com/articles" in href:
                        article_url = href.split("?url=")[
                            -1
                        ].split("&")[0]
                        from urllib.parse import unquote

                        href = unquote(article_url)
                    links.append(Link(link=href, title=title.strip() if title else None))
            page.wait_for_timeout(10000)
    return links
