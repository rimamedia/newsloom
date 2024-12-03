import logging
import random
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from .playwright import USER_AGENTS, get_stream, save_links, update_stream_status


def search_articles(
    stream_id,
    url,
    link_selector,
    search_text,
    article_selector,
    link_selector_type="css",
    article_selector_type="css",
    max_links=10,
):
    logger = logging.getLogger(__name__)
    result = {
        "extracted_count": 0,
        "matched_count": 0,
        "saved_count": 0,
        "links": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        # Get stream in a separate thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            stream_future = executor.submit(get_stream, stream_id)
            stream = stream_future.result()

        if not stream or not stream.source:
            raise ValueError("Stream or stream source not found")

        matching_links = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            try:
                stealth_sync(page)
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)

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
                    title = element.text_content()
                    if href:
                        full_url = urljoin(base_url, href)
                        initial_links.append(
                            {
                                "url": full_url,
                                "title": title.strip() if title else None,
                            }
                        )
                        result["extracted_count"] += 1

                # Visit each link and search for the text
                for link_data in initial_links:
                    try:
                        page.goto(link_data["url"], timeout=60000)
                        page.wait_for_load_state("networkidle", timeout=60000)

                        # Search for text using the appropriate selector method
                        article_content = (
                            page.query_selector(article_selector)
                            if article_selector_type == "css"
                            else page.locator(f"xpath={article_selector}").first
                        )

                        if article_content:
                            content_text = article_content.text_content().lower()
                            if search_text.lower() in content_text:
                                matching_links.append(link_data)
                                result["matched_count"] += 1
                                result["links"].append(link_data)
                                logger.info(
                                    f"Found matching article: {link_data['url']}"
                                )

                    except Exception as e:
                        logger.error(
                            f"Error processing article {link_data['url']}: {str(e)}"
                        )
                        continue

            finally:
                browser.close()

        # Save matching links
        with ThreadPoolExecutor(max_workers=1) as executor:
            save_future = executor.submit(save_links, matching_links, stream)
            result["saved_count"] = save_future.result()

        logger.info(
            f"Successfully processed {result['extracted_count']} links, "
            f"found {result['matched_count']} matches, "
            f"saved {result['saved_count']} new links."
        )

        return result

    except Exception as e:
        logger.error(f"Error processing page: {str(e)}", exc_info=True)
        result["error"] = str(e)

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                update_stream_status,
                stream_id,
                status="failed",
                last_run=timezone.now(),
            )
        raise e
