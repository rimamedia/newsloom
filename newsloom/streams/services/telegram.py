import logging
from datetime import datetime

from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from sources.models import News
from streams.models import Stream


def monitor_telegram_channel(stream_id, posts_limit=20):
    logger = logging.getLogger(__name__)
    result = {
        "processed_count": 0,
        "errors": [],
        "timestamp": timezone.now().isoformat(),
        "stream_id": stream_id,
    }

    try:
        stream = Stream.objects.get(id=stream_id)
        source = stream.source

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                stealth_sync(page)
                page.goto(source.url, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=60000)

                posts = []

                while len(posts) < posts_limit:
                    message_elements = page.query_selector_all(
                        "div.tgme_widget_message_wrap"
                    )

                    for message_element in message_elements:
                        message_text, message_time, message_link = (
                            extract_message_details(message_element)
                        )

                        if message_text and message_time and message_link:
                            # Save to database
                            News.objects.get_or_create(
                                source=source,
                                link=message_link,
                                defaults={
                                    "text": message_text,
                                    "published_at": message_time,
                                },
                            )

                            posts.append(
                                {
                                    "text": message_text,
                                    "timestamp": message_time.strftime(
                                        "%Y-%m-%d %H:%M:%S %Z"
                                    ),
                                    "link": message_link,
                                }
                            )
                            result["processed_count"] += 1

                    # Scroll for more posts if needed
                    if len(posts) < posts_limit:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        page.wait_for_timeout(2000)

            except Exception as e:
                logger.error(f"Error monitoring Telegram channel: {e}")
                result["errors"].append(str(e))
            finally:
                browser.close()

    except Exception as e:
        logger.error(f"Error in Telegram channel monitor task: {str(e)}", exc_info=True)
        result["errors"].append(str(e))
        raise e

    return result


def extract_message_details(message_element):
    """Extract text and timestamp from a message element."""
    try:
        # Extract message text
        text_element = message_element.query_selector("div.tgme_widget_message_text")
        message_text = text_element.inner_text().strip() if text_element else None

        # Get message link
        link_element = message_element.query_selector("a.tgme_widget_message_date")
        message_link = link_element.get_attribute("href") if link_element else None

        # Extract timestamp
        time_element = message_element.query_selector("time")
        if time_element:
            datetime_str = time_element.get_attribute("datetime")
            message_time = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            message_time = message_time.astimezone(timezone.utc)
        else:
            message_time = None

        return message_text, message_time, message_link

    except Exception as e:
        logging.error(f"Error extracting message details: {e}")
        return None, None, None
