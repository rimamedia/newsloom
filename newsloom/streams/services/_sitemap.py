import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from sources.dataclasses import Link


logger = logging.getLogger(__name__)


def parse_lastmod(value: str| None) -> datetime | None:
    if value:
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            ...
    return None


def parse_sitemap(content: str, max_links: int | None = None) -> list[Link]:
    links = []
    soup = BeautifulSoup(content, "lxml")
    elements = soup.findAll("url")
    if max_links:
        elements = elements[:max_links]
    for url_element in elements:
        loc = url_element.find("loc")
        if loc:
            published_at = None
            if lastmod := url_element.find("lastmod"):
                published_at = parse_lastmod(lastmod.text)
            if not published_at:
                published_at = timezone.now()
            links.append(Link(link=loc.text, published_at=published_at))
    return links



def process_sitemap(sitemap_url: str, max_links: int = 100, *args, **kwargs) -> list[Link]:
    response = requests.get(sitemap_url, timeout=10)
    response.raise_for_status()
    return parse_sitemap(response.content, max_links)
