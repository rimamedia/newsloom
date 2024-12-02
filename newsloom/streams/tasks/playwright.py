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

# Add user agents list at the top
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",  # noqa: E501
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",  # noqa: E501
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.0.0",  # noqa: E501
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",  # noqa: E501
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

        # Playwright operations
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            try:
                stealth_sync(page)
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)

                # Get base URL for handling relative URLs
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                elements = page.query_selector_all(link_selector)

                for element in elements[:max_links]:
                    href = element.get_attribute("href")
                    title = element.text_content()
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
            finally:
                browser.close()

        # Save links in a separate thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            save_future = executor.submit(save_links, links, stream)
            save_future.result()  # Wait for save to complete
            result["saved_count"] = len(links)

        # Log success
        logger.info(f"Successfully extracted and saved {len(links)} links.")

        return result  # Return the result dictionary

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
        with transaction.atomic():
            for link_data in links:
                try:
                    news, created = News.objects.get_or_create(
                        source=stream.source,
                        link=link_data["url"],
                        defaults={
                            "title": link_data["title"],
                            "published_at": timezone.now(),
                        },
                    )
                    if created:
                        saved_count += 1
                        logger.info(f"Saved new link: {link_data['url']}")
                    else:
                        logger.debug(f"Link already exists: {link_data['url']}")

                except Exception as e:
                    logger.error(f"Error saving link {link_data['url']}: {e}")
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
