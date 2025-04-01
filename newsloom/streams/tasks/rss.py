import logging
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import feedparser
import requests
from django.db import transaction
from django.utils import timezone
from sources.models import News
from streams.models import Stream

from .link_parser import enrich_link_data


def sanitize_url(url):
    """Ensure URL is properly formatted and encoded."""
    parsed = urlparse(str(url))
    return urlunparse(parsed)


def clean_xml_content(content):
    """Try to clean problematic XML content."""
    # Remove any invalid XML characters
    content = "".join(
        char for char in content if ord(char) < 0xD800 or ord(char) > 0xDFFF
    )

    # Basic attempt to fix common HTML issues in XML
    content = content.replace("&nbsp;", "&#160;")
    content = content.replace("&", "&amp;")
    return content


def parse_rss_feed(stream_id, url, max_items=10, parse_now=True):
    """
    Parse an RSS feed and extract entries.

    Args:
        stream_id: ID of the stream
        url: URL of the RSS feed to parse
        max_items: Maximum number of items to process
        parse_now: Whether to parse links with Articlean immediately (True)
            or mark for later processing (False)

    Returns:
        Dict containing parsing results
    """
    logger = logging.getLogger(__name__)
    result = {
        "processed_count": 0,
        "errors": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        # Sanitize the URL
        clean_url = sanitize_url(url)
        logger.info(f"Fetching RSS feed from {clean_url}")

        # First try direct parsing
        feed = feedparser.parse(clean_url)

        # If there's a parsing error, try to clean the content first
        if hasattr(feed, "bozo_exception"):
            logger.warning(f"Initial parsing error: {feed.bozo_exception}")

            try:
                # Fetch raw content
                response = requests.get(clean_url, timeout=30)
                response.raise_for_status()
                content = response.text

                # Try to clean the content
                cleaned_content = clean_xml_content(content)

                # Parse the cleaned content
                feed = feedparser.parse(cleaned_content)
                logger.info("Successfully parsed feed after cleaning content")

            except requests.RequestException as e:
                error_msg = f"Error fetching feed: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                raise
            except Exception as e:
                error_msg = f"Error cleaning feed content: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                raise

        # Final check for parsing errors
        if hasattr(feed, "bozo_exception"):
            error_msg = f"Feed parsing error: {feed.bozo_exception}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            if not feed.entries:
                raise Exception(error_msg)
            logger.warning(
                "Continuing despite feed parsing error as entries were found"
            )

        stream = Stream.objects.get(id=stream_id)
        logger.info(
            f"Found {len(feed.entries)} entries in feed, processing up to {max_items}"
        )

        with transaction.atomic():
            for entry in feed.entries[:max_items]:
                published_at = None
                if hasattr(entry, "published_parsed"):
                    published_at = datetime(*entry.published_parsed[:6])

                logger.debug(f"Processing entry: {entry.title}")

                # Create link data for enrichment
                link_data = {
                    "url": entry.link,
                    "title": entry.title,
                    "text": entry.get("description", "")
                    or entry.get("summary", "")
                    or "",
                }

                # Enrich link data with Articlean content
                enriched_data = enrich_link_data(link_data, parse_now=parse_now)

                # Create news entry with enriched data
                defaults = {
                    "title": enriched_data.get("title", entry.title),
                    "published_at": published_at or timezone.now(),
                }

                # Use enriched text if available, otherwise use the original
                if "text" in enriched_data and enriched_data["text"]:
                    defaults["text"] = enriched_data["text"]
                else:
                    defaults["text"] = link_data["text"]

                created = News.objects.get_or_create(
                    source=stream.source,
                    link=entry.link,
                    defaults=defaults,
                )
                if created[1]:  # If new object was created
                    logger.info(f"Created new news entry: {entry.title}")
                else:
                    logger.debug(f"News entry already exists: {entry.title}")
                result["processed_count"] += 1

        stream.last_run = timezone.now()
        stream.save(update_fields=["last_run"])

    except Exception as e:
        logger.error(f"Error processing RSS feed: {str(e)}", exc_info=True)
        result["errors"].append(str(e))
        Stream.update_status(stream_id, status="failed")
        raise e

    return result
