from datetime import datetime
from urllib.parse import urlparse, urlunparse

import feedparser
import requests
from feedparser.util import FeedParserDict

from sources.dataclasses import Link


def sanitize_url(url: str) -> str:
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


def bozo_exception_processing(url: str) -> FeedParserDict:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    content = response.text

    # Try to clean the content
    cleaned_content = clean_xml_content(content)

    # Parse the cleaned content
    feed = feedparser.parse(cleaned_content)

    if hasattr(feed, "bozo_exception"):
        if not feed.entries:
            raise Exception(f"Feed parsing error: {feed.bozo_exception}")
    return feed


def rss_feed_parser(url: str, max_items: int = 10) -> list[Link]:
    links = []

        # First try direct parsing
    feed = feedparser.parse(url)
    if hasattr(feed, "bozo_exception"):
        feed = bozo_exception_processing(url)

    for entry in feed.entries[:max_items]:
        published_at = None
        if hasattr(entry, "published_parsed"):
            published_at = datetime(*entry.published_parsed[:6])
        text = entry.get("description", None) or entry.get("summary", None)
        links.append(Link(link=entry.link, title=entry.title, text=text, published_at=published_at))
    return links
