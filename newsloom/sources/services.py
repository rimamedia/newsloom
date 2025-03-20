from django.db import transaction
from django.utils import timezone

from sources.models import News, Source
from sources.dataclasses import Link


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
            published_at=link.published_at or timezone.now(),
        )
        created_news_count += 1
    return created_news_count
