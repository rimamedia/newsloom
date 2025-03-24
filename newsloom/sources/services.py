from datetime import datetime

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from sources.models import News, Source
from sources.dataclasses import Link
from streams.models import Stream


@transaction.atomic
def create_news_from_links(source: Source, links: list[Link]) -> int:
    created_news_count = 0
    for link in links:
        if not link.link.startswith(("http://", "https://")):
            continue
        if News.objects.filter(source=source, link=link.link).exists():
            continue
        title = ''
        if link.title:
            title = link.title.strip()[:255]
        if not title:
            title = "Untitled"
        News.objects.create(
            source=source,
            link=link.link,
            title=title,
            text=link.text,
            published_at=link.published_at or timezone.now(),
        )
        created_news_count += 1
    return created_news_count


def get_news_for_send(
        stream: Stream, time_threshold: datetime, batch_size: int, source_types: list[str] | None
) -> QuerySet[News]:
    qs = News.objects.filter(source__in=stream.media.sources.all(), link__isnull=False, created_at__gte=time_threshold)
    if source_types:
        qs = qs.filter(source__type__in=source_types)
    return qs.order_by("created_at")[:batch_size]
