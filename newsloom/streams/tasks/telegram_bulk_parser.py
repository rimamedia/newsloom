import logging
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytz
from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from sources.models import News, Source

logger = logging.getLogger(__name__)


def standardize_url(url):
    """Standardize the Telegram channel URL."""
    parsed = urlparse(url)
    scheme = "https"
    netloc = parsed.netloc
    path = parsed.path.rstrip("/")
    path_parts = path.split("/")

    if len(path_parts) > 1 and path_parts[1] == "s":
        standardized_path = path
    else:
        if len(path_parts) > 1:
            standardized_path = f"/s/{path_parts[1]}"
        else:
            standardized_path = path

    return f"{scheme}://{netloc}{standardized_path}"


def extract_message_details(message_element):
    """Extract text, timestamp and link from a message element."""
    try:
        # Extract message link
        link_element = message_element.query_selector("a.tgme_widget_message_date")
        if not link_element:
            return None, None, None

        message_link = link_element.get_attribute("href")
        if not message_link:
            return None, None, None

        # Extract message text
        possible_text_classes = [
            "tgme_widget_message_text",
            "tgme_widget_message_content",
        ]
        message_text = None
        for class_name in possible_text_classes:
            text_element = message_element.query_selector(f"div.{class_name}")
            if text_element:
                message_text = text_element.inner_text().strip()
                if message_text:
                    break

        if not message_text:
            return None, None, None

        # Extract timestamp
        time_element = message_element.query_selector("time")
        if time_element:
            datetime_str = time_element.get_attribute("datetime")
            if datetime_str:
                message_time = datetime.fromisoformat(
                    datetime_str.replace("Z", "+00:00")
                )
                if message_time.tzinfo is None:
                    message_time = message_time.replace(tzinfo=pytz.utc)
                return message_text, message_time, message_link

        return None, None, None
    except Exception as e:
        logger.error(f"Error extracting message details: {e}")
        return None, None, None


def parse_telegram_channels(
    stream_id, time_window_minutes=60, max_scrolls=20, wait_time=10
):
    """Parse all Telegram sources and collect recent posts."""
    logger.info(f"Starting bulk Telegram channel parsing for stream {stream_id}")
    result = {
        "processed_channels": 0,
        "total_posts": 0,
        "failed_channels": 0,
        "errors": [],
    }

    try:
        # Get all Telegram sources
        sources = Source.objects.filter(type="telegram")
        if not sources.exists():
            logger.warning("No Telegram sources found")
            return result

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            stealth_sync(page)

            for source in sources:
                try:
                    url = standardize_url(source.link)
                    logger.info(f"Processing channel: {url}")

                    # Navigate to channel
                    page.goto(url, timeout=60000)
                    page.wait_for_selector(
                        "div.tgme_widget_message_wrap", timeout=wait_time * 1000
                    )

                    # Set time threshold
                    time_threshold = timezone.now() - timedelta(
                        minutes=time_window_minutes
                    )

                    # Scroll and collect posts
                    posts_found = 0
                    seen_links = set()  # Track seen message links

                    for _ in range(max_scrolls):
                        messages = page.query_selector_all(
                            "div.tgme_widget_message_wrap"
                        )
                        new_messages_found = False

                        for msg_elem in messages:
                            text, timestamp, message_link = extract_message_details(
                                msg_elem
                            )

                            if (
                                not all([text, timestamp, message_link])
                                or message_link in seen_links
                            ):
                                continue

                            seen_links.add(message_link)

                            if timestamp >= time_threshold:
                                # Create news entry if it doesn't exist
                                _, created = News.objects.get_or_create(
                                    source=source,
                                    link=message_link,
                                    defaults={
                                        "title": text[:255],
                                        "text": text,
                                        "published_at": timestamp,
                                    },
                                )
                                if created:
                                    posts_found += 1
                                    new_messages_found = True

                        # Scroll down
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(2)

                        # If no new messages were found in this scroll, we can stop
                        if not new_messages_found:
                            break

                    result["processed_channels"] += 1
                    result["total_posts"] += posts_found
                    logger.info(f"Processed {posts_found} new posts from {source.name}")

                except Exception as e:
                    error_msg = f"Error processing channel {source.name}: {str(e)}"
                    logger.error(error_msg)
                    result["failed_channels"] += 1
                    result["errors"].append(error_msg)

            browser.close()

        return result

    except Exception as e:
        logger.error(f"Bulk parsing failed: {str(e)}")
        raise
