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

# Context options optimized for memory usage




# def get_stream(stream_id):
#     """Retrieve the stream configuration and details from the database."""
#     try:
#         return Stream.objects.get(id=stream_id)
#     finally:
#         connection.close()


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
                    title = str(link_data.get("title", "")).strip() or "Untitled"
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


def update_stream_status(stream_id, status=None):
    """Update the stream's status and timing."""
    try:
        if status:
            Stream.update_status(stream_id, status=status)
    finally:
        connection.close()
