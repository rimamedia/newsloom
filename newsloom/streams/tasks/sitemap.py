import logging
from datetime import datetime

import requests
from defusedxml import ElementTree as ET
from django.db import transaction
from django.utils import timezone
from sources.models import News
from streams.models import Stream

from .link_parser import enrich_link_data


def parse_sitemap(
    stream_id, sitemap_url, max_links=100, follow_next=False, parse_now=True
):
    """
    Parse a sitemap XML file and extract URLs.

    Args:
        stream_id: ID of the stream
        sitemap_url: URL of the sitemap to parse
        max_links: Maximum number of links to process
        follow_next: Whether to follow next page links in the sitemap
        parse_now: Whether to parse links with Articlean immediately (True)
            or mark for later processing (False)

    Returns:
        Dict containing parsing results
    """
    logger = logging.getLogger(__name__)
    result = {
        "processed_count": 0,
        "urls": [],
        "errors": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        stream = Stream.objects.get(id=stream_id)

        with transaction.atomic():
            for url_element in root.findall(".//url")[:max_links]:
                loc = url_element.find("loc")
                lastmod = url_element.find("lastmod")

                if loc is not None:
                    process_url(stream, loc.text, lastmod, parse_now=parse_now)
                    result["urls"].append(loc.text)
                    result["processed_count"] += 1

        stream.last_run = timezone.now()
        stream.save(update_fields=["last_run"])

    except requests.Timeout:
        error_msg = f"Timeout while fetching sitemap from {sitemap_url}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
        Stream.update_status(stream_id, status="failed")
        raise
    except Exception as e:
        logger.error(f"Error processing sitemap: {str(e)}", exc_info=True)
        result["errors"].append(str(e))
        Stream.update_status(stream_id, status="failed")
        raise e

    return result


def process_url(stream, url, lastmod, parse_now=True):
    """
    Process a URL from a sitemap and save it to the database.

    Args:
        stream: Stream object
        url: URL to process
        lastmod: Last modified date element from sitemap
        parse_now: Whether to parse links with Articlean immediately
    """
    published_at = None
    if lastmod is not None:
        try:
            published_at = datetime.fromisoformat(
                lastmod.text.strip().replace("Z", "+00:00")
            )
        except ValueError:
            pass

    # Create link data for enrichment
    link_data = {
        "url": url,
        "title": None,  # No title available from sitemap
    }

    # Enrich link data with Articlean content
    enriched_data = enrich_link_data(link_data, parse_now=parse_now)

    # Create news entry with enriched data
    defaults = {
        "published_at": published_at or timezone.now(),
    }

    # Add title and text if available from enrichment
    if "title" in enriched_data and enriched_data["title"]:
        defaults["title"] = enriched_data["title"]

    if "text" in enriched_data and enriched_data["text"]:
        defaults["text"] = enriched_data["text"]

    News.objects.get_or_create(
        source=stream.source,
        link=url,
        defaults=defaults,
    )
