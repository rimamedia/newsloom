import logging
import random
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

from django.db import connection, transaction
from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from sources.models import News
from streams.models import Stream

# Browser launch options optimized for container environment
BROWSER_OPTIONS = {
    "headless": True,  # Always use headless mode in container
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--single-process",
        "--no-zygote",
        "--js-flags=--max-old-space-size=2048",
        "--disable-extensions",
        "--disable-component-extensions-with-background-pages",
        "--disable-default-apps",
        "--mute-audio",
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-breakpad",
        "--disable-client-side-phishing-detection",
        "--disable-component-update",
        "--disable-features=TranslateUI,BlinkGenPropertyTrees",
        "--disable-ipc-flooding-protection",
        "--disable-prompt-on-repost",
        "--disable-renderer-backgrounding",
        "--force-color-profile=srgb",
        "--metrics-recording-only",
        "--no-first-run",
    ],
}

# Context options optimized for memory usage
CONTEXT_OPTIONS = {
    "viewport": {"width": 1280, "height": 720},
    "java_script_enabled": True,
    "bypass_csp": False,
    "offline": False,
}

# User agents list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",  # noqa E501
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.0.0",  # noqa E501
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",  # noqa E501
]


def extract_links(stream_id, url, link_selector, max_links=100):
    logger = logging.getLogger(__name__)
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

        links = []

        # Playwright operations with optimized settings
        with sync_playwright() as p:
            browser = p.chromium.launch(**BROWSER_OPTIONS)
            try:
                context_options = {
                    **CONTEXT_OPTIONS,
                    "user_agent": random.choice(USER_AGENTS),
                }
                context = browser.new_context(**context_options)
                try:
                    page = context.new_page()
                    try:
                        stealth_sync(page)
                        # Reduced timeout and added waitUntil option
                        page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        # Reduced timeout for network idle
                        page.wait_for_load_state("networkidle", timeout=30000)

                        # Get base URL for handling relative URLs
                        parsed_url = urlparse(url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                        elements = page.query_selector_all(link_selector)

                        for element in elements[:max_links]:
                            try:
                                href = element.get_attribute("href")
                                # Get text content without timeout
                                title = element.evaluate("el => el.textContent")
                                if href:
                                    # Convert relative URLs to absolute URLs
                                    full_url = urljoin(base_url, href)
                                    link_data = {
                                        "url": full_url,
                                        "title": title.strip() if title else None,
                                    }
                                    links.append(link_data)
                                    result["links"].append(link_data)
                                    result["extracted_count"] += 1
                            except Exception as e:
                                logger.warning(f"Error processing element: {str(e)}")
                                continue
                    finally:
                        if page:
                            page.close()
                finally:
                    if context:
                        context.close()
            finally:
                if browser:
                    browser.close()

        # Save links in a separate thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            save_future = executor.submit(save_links, links, stream)
            save_future.result()  # Wait for save to complete
            result["saved_count"] = len(links)

        # Log success
        logger.info(f"Successfully extracted and saved {len(links)} links.")

        return result

    except Exception as e:
        logger.error(f"Error processing page: {str(e)}", exc_info=True)
        result["error"] = str(e)

        # Update stream status on failure
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                update_stream_status,
                stream_id,
                status="failed",
                last_run=timezone.now(),
            )
        raise e


def get_stream(stream_id):
    """Retrieve the stream configuration and details from the database."""
    try:
        return Stream.objects.get(id=stream_id)
    finally:
        connection.close()


def save_links(links, stream):
    """Save the extracted links to the database."""
    logger = logging.getLogger(__name__)
    saved_count = 0

    try:
        # Validate stream and source
        if not stream:
            logger.error("Stream object is None")
            return 0

        if not stream.source:
            logger.error(f"No source found for stream {stream.id}")
            return 0

        logger.info(f"Attempting to save {len(links)} links for stream {stream.id}")
        logger.info(f"Stream source: {stream.source.name}")

        with transaction.atomic():
            for link_data in links:
                try:
                    # Validate link data
                    if not isinstance(link_data, dict):
                        logger.warning(f"Invalid link data format: {link_data}")
                        continue

                    url = link_data.get("url")
                    if not url:
                        logger.warning("Skipping link with no URL")
                        continue

                    if not url.startswith(("http://", "https://")):
                        logger.warning(f"Skipping invalid URL format: {url}")
                        continue

                    logger.debug(f"Processing link: {url}")

                    # Check for existing link
                    existing = News.objects.filter(
                        source=stream.source, link=url
                    ).exists()

                    if existing:
                        logger.debug(f"Link already exists: {url}")
                        continue

                    # Prepare title
                    title = link_data.get("title", "").strip()
                    if not title:
                        title = "Untitled"
                    title = title[:255]  # Truncate to max length

                    # Create news entry
                    news = News.objects.create(
                        source=stream.source,
                        link=url,
                        title=title,
                        published_at=timezone.now(),
                    )
                    saved_count += 1
                    logger.info(
                        f"Successfully saved news entry {news.id} with URL: {url}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error saving link {link_data.get('url')}: {str(e)}",
                        exc_info=True,
                    )
                    continue

            logger.info(
                f"Saved {saved_count} new links out of {len(links)} total links"
            )
            return saved_count

    except Exception as e:
        logger.exception(f"Transaction failed while saving links: {e}")
        raise
    finally:
        connection.close()


def update_stream_status(stream_id, status=None, last_run=None):
    """Update the stream's status and last run time."""
    try:
        update_fields = {}
        if status:
            update_fields["status"] = status
        if last_run:
            update_fields["last_run"] = last_run

        Stream.objects.filter(id=stream_id).update(**update_fields)
    finally:
        connection.close()
