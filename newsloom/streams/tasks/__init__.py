from .sitemap import (
    SitemapNewsParsingTask,
    SitemapBlogParsingTask,
)
# from .rss import RSSFeedParsingTask
# from .web import WebArticleScrapingTask
# from .telegram import TelegramChannelMonitorTask

# Map stream types to their corresponding Luigi task classes
TASK_MAPPING = {
    'sitemap_news': SitemapNewsParsingTask,
    # 'sitemap_blog': SitemapBlogParsingTask,
    # 'rss_feed': RSSFeedParsingTask,
    # 'web_article': WebArticleScrapingTask,
    # 'telegram_channel': TelegramChannelMonitorTask,
}

def get_task_class(stream_type):
    """Get the appropriate Luigi task class for a given stream type."""
    return TASK_MAPPING.get(stream_type) 