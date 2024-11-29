import logging
import tempfile
from datetime import datetime

import feedparser
import luigi
from django.db import transaction
from django.utils import timezone
from sources.models import News


class RSSFeedParsingTask(luigi.Task):
    stream_id = luigi.IntParameter()
    feed_url = luigi.Parameter(description="URL of the RSS feed to parse")
    max_entries = luigi.IntParameter(
        default=100, description="Maximum number of entries to process"
    )
    scheduled_time = luigi.DateTimeParameter()

    @classmethod
    def get_config_example(cls):
        return {
            "feed_url": "https://example.com/feed.xml",
            "max_entries": 100,
        }

    def run(self):
        from streams.models import Stream

        logger = logging.getLogger(__name__)

        try:
            feed = feedparser.parse(self.feed_url)
            logger.info(f"Fetched RSS feed from {self.feed_url}")

            stream = Stream.objects.get(id=self.stream_id)

            with transaction.atomic():
                for entry in feed.entries[: self.max_entries]:
                    published_at = None
                    if hasattr(entry, "published_parsed"):
                        published_at = datetime(*entry.published_parsed[:6])

                    News.objects.get_or_create(
                        source=stream.source,
                        link=entry.link,
                        defaults={
                            "title": entry.title,
                            "description": entry.get("description", ""),
                            "published_at": published_at or timezone.now(),
                        },
                    )

            stream.last_run = timezone.now()
            stream.save(update_fields=["last_run"])

        except Exception as e:
            logger.error(f"Error processing RSS feed: {str(e)}", exc_info=True)
            Stream.objects.filter(id=self.stream_id).update(
                status="failed", last_run=timezone.now()
            )
            raise e

    def output(self):
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"rss_task_{self.stream_id}_",
            suffix=f'_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            delete=False,
        )
        return luigi.LocalTarget(temp_file.name)
