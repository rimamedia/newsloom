import logging
from datetime import datetime

import feedparser
from django.db import transaction
from django.utils import timezone
from sources.models import News
from streams.models import Stream


def parse_rss_feed(stream_id, url, max_items=10):
    logger = logging.getLogger(__name__)
    result = {
        "processed_count": 0,
        "errors": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        feed = feedparser.parse(str(url))
        logger.info(f"Fetched RSS feed from {url}")

        stream = Stream.objects.get(id=stream_id)

        with transaction.atomic():
            for entry in feed.entries[:max_items]:
                published_at = None
                if hasattr(entry, "published_parsed"):
                    published_at = datetime(*entry.published_parsed[:6])

                News.objects.get_or_create(
                    source=stream.source,
                    link=entry.link,
                    defaults={
                        "title": entry.title,
                        "description": entry.get("description", ""),
                        "published_at": published_at or timezone.now(),
                    },
                )
                result["processed_count"] += 1

        stream.last_run = timezone.now()
        stream.save(update_fields=["last_run"])

    except Exception as e:
        logger.error(f"Error processing RSS feed: {str(e)}", exc_info=True)
        result["errors"].append(str(e))
        Stream.objects.filter(id=stream_id).update(
            status="failed", last_run=timezone.now()
        )
        raise e

    return result
