import logging
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Page

from sources.dataclasses import Link

logger = logging.getLogger(__name__)


def article_searcher_extractor(
        page: Page,
        url: str,
        link_selector,
        search_text,
        article_selector,
        link_selector_type="css",
        article_selector_type="css",
        max_links=10,
) -> list[Link]:
    links = []

    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Get all links using the appropriate selector method
    elements = (
        page.query_selector_all(link_selector)
        if link_selector_type == "css"
        else page.locator(f"xpath={link_selector}").all()
    )
    initial_links = []
    for element in elements[:max_links]:
        href = element.get_attribute("href")
        if href:
            title = element.evaluate("el => el.textContent")
            initial_links.append(Link(link=urljoin(base_url, href), title=title.strip() if title else None))

    for link_data in initial_links:
        page.goto(link_data.link, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)

        # Search for text using the appropriate selector method
        article_content = (
            page.query_selector(article_selector)
            if article_selector_type == "css"
            else page.locator(f"xpath={article_selector}").first
        )

        if not article_content:
            continue

        content_text = article_content.text_content().lower()
        if search_text.lower() in content_text:
            links.append(link_data)

    return links
