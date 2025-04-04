import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict
from urllib.parse import urlparse

import pytz
from asgiref.sync import sync_to_async
from django.utils import timezone
from playwright.async_api import async_playwright, Page
from playwright_stealth import stealth_async
from sources.models import News, Source

logger = logging.getLogger(__name__)


class TelegramParsingError(Exception):
    """Base exception for Telegram parsing errors."""

    pass


class ChannelNavigationError(TelegramParsingError):
    """Raised when unable to navigate to or load a channel."""

    pass


class MessageExtractionError(TelegramParsingError):
    """Raised when unable to extract message details."""

    pass


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


async def extract_message_details(message_element):
    """Extract text, timestamp and link from a message element."""
    try:
        link_element = await message_element.query_selector(
            "a.tgme_widget_message_date"
        )
        if not link_element:
            return None, None, None

        message_link = await link_element.get_attribute("href")
        if not message_link:
            return None, None, None

        # TODO: fix text extraction
        possible_text_classes = [
            "tgme_widget_message_text",
            "tgme_widget_message_content",
        ]
        message_text = None
        for class_name in possible_text_classes:
            text_element = await message_element.query_selector(f"div.{class_name}")
            if text_element:
                message_text = await text_element.inner_text()
                message_text = message_text.strip()
                if message_text:
                    break

        if not message_text:
            return None, None, None

        time_element = await message_element.query_selector("time")
        if time_element:
            datetime_str = await time_element.get_attribute("datetime")
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


async def process_single_channel(
    page: Page,
    source: Source,
    time_threshold: datetime,
    max_scrolls: int = 20,
    wait_time: int = 10,
) -> Dict:
    """Process a single Telegram channel and return results.

    Args:
        page: Playwright page object
        source: Source model instance
        time_threshold: Datetime threshold for posts
        max_scrolls: Maximum number of scroll attempts
        wait_time: Wait time between actions in seconds

    Returns:
        Dict containing processing results and statistics
    """
    start_time = timezone.now()
    channel_result = {
        "channel_name": source.name,
        "success": False,
        "posts_processed": 0,
        "error": None,
        "duration": None,
    }

    try:
        url = standardize_url(source.link)
        logger.info(
            f"Processing channel: {url}",
            extra={
                "channel": source.name,
                "url": url,
                "start_time": start_time.isoformat(),
            },
        )

        # Navigate to channel with timeout
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("div.tgme_widget_message_wrap", timeout=wait_time * 1000)
        except Exception as e:
            raise ChannelNavigationError(f"Failed to navigate to channel: {str(e)}")

        # Scroll and collect posts
        posts_found = 0
        seen_links = set()

        for scroll_num in range(max_scrolls):
            try:
                messages = await page.query_selector_all("div.tgme_widget_message_wrap")
                new_messages_found = False

                for msg_elem in messages:
                    try:
                        text, timestamp, message_link = await extract_message_details(
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

                    except MessageExtractionError as e:
                        logger.warning(
                            f"Failed to extract message from {source.name}",
                            extra={
                                "channel": source.name,
                                "error": str(e),
                                "scroll_number": scroll_num,
                            },
                        )
                        continue

                # Scroll down
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

                if not new_messages_found:
                    break

            except Exception as e:
                logger.warning(
                    f"Error during scroll iteration for {source.name}",
                    extra={
                        "channel": source.name,
                        "error": str(e),
                        "scroll_number": scroll_num,
                    },
                )
                continue

        channel_result.update(
            {
                "success": True,
                "posts_processed": posts_found,
                "duration": (timezone.now() - start_time).total_seconds(),
            }
        )

        logger.info(
            f"Successfully processed channel: {source.name}",
            extra={
                "channel": source.name,
                "posts_processed": posts_found,
                "duration": channel_result["duration"],
                "success": True,
            },
        )

    except Exception as e:
        duration = (timezone.now() - start_time).total_seconds()
        error_msg = f"Failed to process channel {source.name}: {str(e)}"
        logger.error(
            error_msg,
            extra={
                "channel": source.name,
                "error": str(e),
                "error_type": e.__class__.__name__,
                "duration": duration,
            },
        )
        channel_result.update({"success": False, "error": str(e), "duration": duration})

    return channel_result


async def parse_telegram_channels(
    stream_id: int,
    time_window_minutes: int = 60,
    max_scrolls: int = 20,
    wait_time: int = 10,
) -> Dict:
    """Parse all Telegram sources and collect recent posts."""
    start_time = timezone.now()
    result = {
        "stream_id": stream_id,
        "successful_channels": [],
        "failed_channels": [],
        "total_posts": 0,
        "execution_time": None,
        "start_time": start_time.isoformat(),
    }

    try:
        # Get all Telegram sources
        sources = await sync_to_async(list)(Source.objects.filter(type="telegram"))
        if not sources:
            logger.warning("No Telegram sources found", extra={"stream_id": stream_id})
            return result

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await stealth_async(page)

            time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)

            for source in sources:
                channel_result = await process_single_channel(
                    page=page,
                    source=source,
                    time_threshold=time_threshold,
                    max_scrolls=max_scrolls,
                    wait_time=wait_time,
                )

                if channel_result["success"]:
                    result["successful_channels"].append(
                        {
                            "name": channel_result["channel_name"],
                            "posts_processed": channel_result["posts_processed"],
                            "duration": channel_result["duration"],
                        }
                    )
                    result["total_posts"] += channel_result["posts_processed"]
                else:
                    result["failed_channels"].append(
                        {
                            "name": channel_result["channel_name"],
                            "error": channel_result["error"],
                            "duration": channel_result["duration"],
                        }
                    )

            await browser.close()

        execution_time = (timezone.now() - start_time).total_seconds()
        result["execution_time"] = execution_time

        logger.info(
            "Completed Telegram channel parsing",
            extra={
                "stream_id": stream_id,
                "successful_channels": len(result["successful_channels"]),
                "failed_channels": len(result["failed_channels"]),
                "total_posts": result["total_posts"],
                "execution_time": execution_time,
            },
        )

        return result

    except Exception as e:
        execution_time = (timezone.now() - start_time).total_seconds()
        error_msg = f"Bulk parsing failed: {str(e)}"
        logger.error(
            error_msg,
            extra={
                "stream_id": stream_id,
                "error": str(e),
                "error_type": e.__class__.__name__,
                "execution_time": execution_time,
            },
        )
        raise


def run_telegram_parser(stream_id, **kwargs):
    """Run synchronous wrapper for the async parser."""
    return asyncio.run(parse_telegram_channels(stream_id, **kwargs))
