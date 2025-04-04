import logging
import random

from urllib.parse import urljoin, urlparse
from typing import Callable

from django.conf import settings
from playwright.sync_api import Page
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from sources.dataclasses import Link


logger = logging.getLogger(__name__)

class PlaywrightException(Exception):
    ...


def get_random_user_agent() -> str:
    return random.choice(settings.PLAYWRIGHT_USER_AGENTS)


def playwright_extractor(url: str, extractor: Callable[[Page, ...], list[Link]]) -> list[Link]:
    browser = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**settings.PLAYWRIGHT_BROWSER_OPTIONS)
            context = browser.new_context(user_agent=get_random_user_agent(), **settings.PLAYWRIGHT_CONTEXT_OPTIONS)
            page = context.new_page()
            stealth_sync(page)
            # Reduced timeout with default wait_until option
            page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT)
            # Reduced timeout for network idle
            page.wait_for_load_state("networkidle", timeout=settings.PLAYWRIGHT_TIMEOUT)

            return extractor(page)
    except Exception as e:
        if browser and browser.is_connected():
            browser.close()
        raise PlaywrightException() from e



def link_extractor(page: Page, url: str, link_selector: str, max_links: int = 100) -> list[Link]:
    links = []

    # Get base URL for handling relative URLs
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    for element in page.query_selector_all(link_selector)[:max_links]:
        href = element.get_attribute("href")
        # Get text content without timeout
        if href:
            title = element.evaluate("el => el.textContent") or ""
            if title:
                title = title.strip()
            links.append(Link(link=urljoin(base_url, href), title=title))

    return links
