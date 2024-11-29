import json
import logging
import tempfile
from datetime import datetime

import luigi
import pytz
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from sources.models import News


class TelegramChannelMonitorTask(luigi.Task):
    stream_id = luigi.IntParameter()
    scheduled_time = luigi.DateTimeParameter()
    posts_limit = luigi.IntParameter(default=20)

    @classmethod
    def get_config_example(cls):
        return {
            "posts_limit": 20,
        }

    def extract_message_details(self, message_element):
        """Extract text and timestamp from a message element."""
        try:
            # Extract message text
            text_element = message_element.query_selector(
                "div.tgme_widget_message_text"
            )
            message_text = text_element.inner_text().strip() if text_element else None

            # Get message link
            link_element = message_element.query_selector("a.tgme_widget_message_date")
            message_link = link_element.get_attribute("href") if link_element else None

            # Extract timestamp
            time_element = message_element.query_selector("time")
            if time_element:
                datetime_str = time_element.get_attribute("datetime")
                message_time = datetime.fromisoformat(
                    datetime_str.replace("Z", "+00:00")
                )
                message_time = message_time.astimezone(pytz.utc)
                return message_text, message_time, message_link
        except Exception as e:
            logging.error(f"Error extracting message details: {e}")
        return None, None, None

    def run(self):
        # Get source from stream_id
        from streams.models import Stream

        stream = Stream.objects.get(id=self.stream_id)
        source = stream.source

        if not source or not source.link:
            raise ValueError("No valid source or source URL provided")

        posts = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            stealth_sync(page)

            try:
                # Navigate to channel
                page.goto(source.link, timeout=60000)
                page.wait_for_selector("div.tgme_widget_message_wrap", timeout=10000)

                # Collect posts
                while len(posts) < self.posts_limit:
                    message_elements = page.query_selector_all(
                        "div.tgme_widget_message_wrap"
                    )

                    for msg_elem in message_elements:
                        if len(posts) >= self.posts_limit:
                            break

                        message_text, message_time, message_link = (
                            self.extract_message_details(msg_elem)
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

                    # Scroll for more posts if needed
                    if len(posts) < self.posts_limit:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        page.wait_for_timeout(2000)

            except Exception as e:
                logging.error(f"Error monitoring Telegram channel: {e}")
            finally:
                browser.close()

        # Save results
        with self.output().open("w") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)

    def output(self):
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"telegram_task_{self.stream_id}_",
            suffix=f'_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            delete=False,
        )
        return luigi.LocalTarget(temp_file.name)
