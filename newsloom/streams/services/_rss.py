import logging
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import feedparser
import requests
from django.db import transaction
from django.utils import timezone
from sources.models import News
from sources.dataclasses import Link
from streams.models import Stream


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


def parse_rss_feed(url: str, max_items: int = 10) -> list[Link]:
    links = []

        # First try direct parsing
    feed = feedparser.parse(url)
    

    for entry in feed.entries[:max_items]:
        published_at = None
        if hasattr(entry, "published_parsed"):
            published_at = datetime(*entry.published_parsed[:6])
        text = entry.get("description", None) or entry.get("summary", None)
        links.append(Link(link=entry.link, text=text, published_at=published_at))
    return links

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


