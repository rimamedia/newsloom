import json
import logging
from collections import namedtuple

import requests
from django.conf import settings

from sources.dataclasses import Link


logger = logging.getLogger(__name__)


ParseLinkResult = namedtuple("ParseLinkResult", ["title", "text"])


class ParseLinkException(Exception):
    ...


def parse_link(url: str, timeout: int = 30) -> ParseLinkResult | None:

    headers = {
        "x-api-key": settings.ARTICLEAN_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            f"{settings.ARTICLEAN_API_URL}/process-url", headers=headers, json={"url": url}, timeout=timeout
        )
        if response.status_code != requests.codes.ok:
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ParseLinkException from e
    else:
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ParseLinkException() from e
        else:
            if data.get("result", {}).get("is_success"):
                return ParseLinkResult(data["result"]["data"]["title"], data["result"]["data"]["plain_text"])
            raise ParseLinkException('Parse URL with Articlean failed.')



def enrich_link(
    link: Link
) -> Link:
    try:
        result = parse_link(link.link)
        if result:
            if result.title:
                link.title = result.title
            if result.text:
                link.text = result.text
    except ParseLinkException:
        logger.exception(f"Failed to enrich link with Articlean")
    return link


def enrich_links(links: list[Link]) -> list[Link]:
    for link in links:
        enrich_link(link)
    return links
