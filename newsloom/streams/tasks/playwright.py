import logging
import random
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urljoin, urlparse

import luigi
from django.db import connection, transaction
from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from sources.models import News

# Add user agents list at the top
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",  # noqa: E501
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",  # noqa: E501
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.0.0",  # noqa: E501
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",  # noqa: E501
]


class PlaywrightLinkExtractorTask(luigi.Task):
    """Task for extracting links from webpages using Playwright in stealth mode."""

    # Task parameters
    stream_id = luigi.IntParameter(description="ID of the Stream model instance")
    url = luigi.Parameter(description="URL of the page to scrape")
    link_selector = luigi.Parameter(description="CSS selector for finding links")
    max_links = luigi.IntParameter(
        default=100, description="Maximum number of links to process"
    )
    scheduled_time = luigi.Parameter(description="Scheduled execution time")

    def get_stream(self):
        """Retrieve the stream configuration and details from the database."""
        from streams.models import Stream

        try:
            return Stream.objects.get(id=self.stream_id)
        finally:
            connection.close()

    def save_links(self, links, stream):
        """Save the extracted links to the database."""
        try:
            with transaction.atomic():
                for link_data in links:
                    News.objects.get_or_create(
                        source=stream.source,
                        link=link_data["url"],
                        defaults={
                            "title": link_data["title"],
                            "published_at": timezone.now(),
                        },
                    )
        finally:
            connection.close()

    def update_stream_status(self, stream_id, status=None, last_run=None):
        """Update the stream's status and last run time."""
        from streams.models import Stream

        try:
            update_fields = {}
            if status:
                update_fields["status"] = status
            if last_run:
                update_fields["last_run"] = last_run

            Stream.objects.filter(id=stream_id).update(**update_fields)
        finally:
            connection.close()

    def run(self):
        """Execute the Playwright link extraction task."""
        logger = logging.getLogger(__name__)

        try:
            # Get stream in a separate thread
            with ThreadPoolExecutor(max_workers=1) as executor:
                stream_future = executor.submit(self.get_stream)
                stream = stream_future.result()

            links = []

            # Playwright operations
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()

                try:
                    stealth_sync(page)
                    page.goto(self.url, timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=60000)

                    # Get base URL for handling relative URLs
                    parsed_url = urlparse(self.url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                    elements = page.query_selector_all(self.link_selector)

                    for element in elements[: self.max_links]:
                        href = element.get_attribute("href")
                        title = element.text_content()
                        if href:
                            # Convert relative URLs to absolute URLs
                            full_url = urljoin(base_url, href)
                            links.append(
                                {
                                    "url": full_url,
                                    "title": title.strip() if title else None,
                                }
                            )
                finally:
                    browser.close()

            # Save links in a separate thread
            with ThreadPoolExecutor(max_workers=1) as executor:
                save_future = executor.submit(self.save_links, links, stream)
                save_future.result()  # Wait for save to complete

            # Update stream status
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(
                    self.update_stream_status, self.stream_id, last_run=timezone.now()
                )

        except Exception as e:
            logger.error(f"Error processing page: {str(e)}", exc_info=True)
            # Update stream status on failure
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(
                    self.update_stream_status,
                    self.stream_id,
                    status="failed",
                    last_run=timezone.now(),
                )
            raise e

    def output(self):
        # Create a temporary file with a unique name
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"playwright_task_{self.stream_id}_",
            suffix=f'_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            delete=False,
        )
        return luigi.LocalTarget(temp_file.name)
