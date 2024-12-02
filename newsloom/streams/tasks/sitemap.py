import logging
from datetime import datetime

import requests
from defusedxml import ElementTree as ET
from django.db import transaction
from django.utils import timezone
from sources.models import News
from streams.models import Stream


def parse_sitemap(stream_id, sitemap_url, max_links=100, follow_next=False):
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
                    process_url(stream, loc.text, lastmod)
                    result["urls"].append(loc.text)
                    result["processed_count"] += 1

        stream.last_run = timezone.now()
        stream.save(update_fields=["last_run"])

    except requests.Timeout:
        error_msg = f"Timeout while fetching sitemap from {sitemap_url}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
        Stream.objects.filter(id=stream_id).update(
            status="failed", last_run=timezone.now()
        )
        raise
    except Exception as e:
        logger.error(f"Error processing sitemap: {str(e)}", exc_info=True)
        result["errors"].append(str(e))
        Stream.objects.filter(id=stream_id).update(
            status="failed", last_run=timezone.now()
        )
        raise e

    return result


def process_url(stream, url, lastmod):
    published_at = None
    if lastmod is not None:
        try:
            published_at = datetime.fromisoformat(
                lastmod.text.strip().replace("Z", "+00:00")
            )
        except ValueError:
            pass

    News.objects.get_or_create(
        source=stream.source,
        link=url,
        defaults={
            "published_at": published_at or timezone.now(),
        },
    )
