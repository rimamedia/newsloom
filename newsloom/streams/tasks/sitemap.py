import logging
import tempfile
from datetime import datetime

import luigi
import requests
from defusedxml import ElementTree as ET
from django.db import transaction
from django.utils import timezone
from sources.models import News


class BaseSitemapTask(luigi.Task):
    """Base task for processing sitemaps with configurable parameters."""

    # Common parameters
    stream_id = luigi.IntParameter(description="ID of the Stream model instance")
    sitemap_url = luigi.Parameter(description="URL of the sitemap to parse")
    max_links = luigi.IntParameter(
        default=100, description="Maximum number of links to process"
    )
    scheduled_time = luigi.Parameter(description="Scheduled execution time")
    follow_next = luigi.BoolParameter(
        default=False, description="Whether to follow next page links in sitemaps"
    )

    def run(self):
        from streams.models import Stream

        logger = logging.getLogger(__name__)

        try:
            response = requests.get(self.sitemap_url, timeout=60)
            response.raise_for_status()

            logger.info(f"Fetched sitemap from {self.sitemap_url}")

            root = ET.fromstring(response.content)
            ns = {"ns": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
            url_tag = "ns:url" if ns else "url"
            loc_tag = "ns:loc" if ns else "loc"
            lastmod_tag = "ns:lastmod" if ns else "lastmod"

            stream = Stream.objects.get(id=self.stream_id)

            processed_links = 0
            with transaction.atomic():
                for url_elem in root.findall(f".//{url_tag}", ns):
                    if processed_links >= self.max_links:
                        break

                    loc = url_elem.find(f".//{loc_tag}", ns)
                    lastmod = url_elem.find(f".//{lastmod_tag}", ns)

                    if loc is not None:
                        self.process_url(stream, loc.text.strip(), lastmod)
                        processed_links += 1

            stream.last_run = timezone.now()
            stream.save(update_fields=["last_run"])

        except Exception as e:
            logger.error(f"Error processing sitemap: {str(e)}", exc_info=True)
            Stream.objects.filter(id=self.stream_id).update(
                status="failed", last_run=timezone.now()
            )
            raise e

    def output(self):
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"sitemap_task_{self.stream_id}_",
            suffix=f'_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            delete=False,
        )
        return luigi.LocalTarget(temp_file.name)

    def process_url(self, stream, url, lastmod):
        """Process a single URL from the sitemap."""
        raise NotImplementedError


class SitemapNewsParsingTask(BaseSitemapTask):
    """Task implementation for parsing news-specific sitemaps."""

    def process_url(self, stream, url, lastmod):
        published_at = None
        if lastmod is not None:
            try:
                published_at = datetime.fromisoformat(
                    lastmod.text.strip().replace("Z", "+00:00")
                )
            except ValueError:
                pass

        News.objects.get_or_create(
            source=stream.source,
            link=url,
            defaults={
                "published_at": published_at or timezone.now(),
            },
        )


class SitemapBlogParsingTask(BaseSitemapTask):
    """Task implementation for parsing blog-specific sitemaps."""

    def process_url(self, stream, url, lastmod):
        published_at = None
        if lastmod is not None:
            try:
                published_at = datetime.fromisoformat(
                    lastmod.text.strip().replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # You might want to add additional blog-specific processing here
        News.objects.get_or_create(
            source=stream.source,
            link=url,
            defaults={
                "published_at": published_at or timezone.now(),
            },
        )
