import logging

from .playwright import PlaywrightLinkExtractorTask
from .sitemap import SitemapBlogParsingTask, SitemapNewsParsingTask
from .telegram_publisher import TelegramPublishingTask
from .telegram_test import TelegramTestTask

# Map stream types to their corresponding Luigi task classes
TASK_MAPPING = {
    "sitemap_news": SitemapNewsParsingTask,
    "sitemap_blog": SitemapBlogParsingTask,
    "playwright_link_extractor": PlaywrightLinkExtractorTask,
    "telegram_publish": TelegramPublishingTask,
    "telegram_test": TelegramTestTask,
}


def get_task_class(stream_type):
    """Get the appropriate task class for a given stream type."""
    logger = logging.getLogger(__name__)

    logger.debug(f"Looking for task class for stream_type: {stream_type}")
    logger.debug(f"Available task mappings: {TASK_MAPPING}")

    task_class = TASK_MAPPING.get(stream_type)

    if task_class is None:
        logger.error(f"No task class found for stream_type: {stream_type}")
    else:
        logger.debug(f"Found task class: {task_class}")

    return task_class
