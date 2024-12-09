import asyncio
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytz
from asgiref.sync import sync_to_async
from django.utils import timezone
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from sources.models import News, Source

logger = logging.getLogger(__name__)


def standardize_url(url):
    """Standardize the Telegram channel URL to t.me/s format."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")  # Remove trailing slash
    path_parts = path.split("/")

    # Extract channel name from path
    channel_name = None
    if len(path_parts) > 1 and path_parts[1] == "s":
        channel_name = path_parts[2] if len(path_parts) > 2 else None
    else:
        channel_name = path_parts[1] if len(path_parts) > 1 else None

    if not channel_name:
        raise ValueError("Could not extract channel name from URL")

    # Always use t.me/s format
    return f"https://t.me/s/{channel_name}"


async def extract_message_details(message_element):
    """Extract text, timestamp and link from a message element."""
    try:
        # Get message link from the date element
        link_element = await message_element.query_selector(
            "a.tgme_widget_message_date"
        )
        if not link_element:
            logger.warning("No link element found")
            return None, None, None

        message_link = await link_element.get_attribute("href")
        if not message_link:
            logger.warning("No href attribute found in link element")
            return None, None, None

        # Try multiple possible text selectors
        message_text = None
        possible_text_selectors = [
            "div.tgme_widget_message_text",
            "div.tgme_widget_message_content",
            "div.message_media_wrap",
            "div.tgme_widget_message_bubble",
        ]

        for selector in possible_text_selectors:
            text_element = await message_element.query_selector(selector)
            if text_element:
                message_text = await text_element.inner_text()
                message_text = message_text.strip()
                if message_text:
                    break

        if not message_text:
            logger.warning(f"No text content found for message {message_link}")
            return None, None, None

        # Get timestamp from time element
        time_element = await message_element.query_selector("time")
        if time_element:
            datetime_str = await time_element.get_attribute("datetime")
            if datetime_str:
                try:
                    message_time = datetime.fromisoformat(
                        datetime_str.replace("Z", "+00:00")
                    )
                    if message_time.tzinfo is None:
                        message_time = message_time.replace(tzinfo=pytz.utc)
                    return message_text, message_time, message_link
                except ValueError as e:
                    logger.error(f"Error parsing datetime {datetime_str}: {e}")
                    return None, None, None
            else:
                logger.warning("No datetime attribute found in time element")
        else:
            logger.warning("No time element found")

        return None, None, None
    except Exception as e:
        logger.error(f"Error extracting message details: {e}", exc_info=True)
        return None, None, None


async def parse_telegram_channels(
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
        sources = await sync_to_async(list)(Source.objects.filter(type="telegram"))
        if not sources:
            logger.warning("No Telegram sources found")
            return result

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa: E501
            )
            page = await context.new_page()
            await stealth_async(page)

            for source in sources:
                try:
                    url = standardize_url(source.link)
                    logger.info(f"Processing channel: {url}")

                    # Navigate to channel with increased timeout
                    await page.goto(url, timeout=60000)
                    await page.wait_for_selector(
                        "div.tgme_widget_message_wrap",
                        timeout=wait_time * 1000,
                        state="visible",  # Wait until element is visible
                    )

                    # Set time threshold
                    time_threshold = timezone.now() - timedelta(
                        minutes=time_window_minutes
                    )

                    # Scroll and collect posts
                    posts_found = 0
                    seen_links = set()
                    last_height = await page.evaluate("document.body.scrollHeight")

                    for scroll in range(max_scrolls):
                        logger.info(f"Scroll attempt {scroll + 1}/{max_scrolls}")

                        messages = await page.query_selector_all(
                            "div.tgme_widget_message_wrap"
                        )
                        logger.info(f"Found {len(messages)} messages on page")

                        new_messages_found = False

                        for msg_elem in messages:
                            text, timestamp, message_link = (
                                await extract_message_details(msg_elem)
                            )

                            if not all([text, timestamp, message_link]):
                                continue

                            if message_link in seen_links:
                                continue

                            seen_links.add(message_link)

                            if timestamp >= time_threshold:
                                try:
                                    _, created = await sync_to_async(
                                        News.objects.get_or_create
                                    )(
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
                                        logger.info(f"Created new post: {message_link}")
                                except Exception as e:
                                    logger.error(f"Error creating news entry: {e}")

                        # Scroll down
                        await page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight)"
                        )
                        await page.wait_for_timeout(2000)

                        # Check if we've reached the bottom
                        new_height = await page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            logger.info("Reached bottom of page")
                            break
                        last_height = new_height

                        if not new_messages_found:
                            logger.info("No new messages found in this scroll")
                            break

                    result["processed_channels"] += 1
                    result["total_posts"] += posts_found
                    logger.info(f"Processed {posts_found} new posts from {source.name}")

                except Exception as e:
                    error_msg = f"Error processing channel {source.name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    result["failed_channels"] += 1
                    result["errors"].append(error_msg)

            await browser.close()

        return result

    except Exception as e:
        logger.error(f"Bulk parsing failed: {str(e)}", exc_info=True)
        raise


def run_telegram_parser(stream_id, **kwargs):
    """Run synchronous wrapper for the async parser."""
    return asyncio.run(parse_telegram_channels(stream_id, **kwargs))
