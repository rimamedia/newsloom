from .sitemap import BaseSitemapConfig
from .rss import RSSFeedConfig
from .web_article import WebArticleConfig
from .telegram import TelegramConfig, TelegramPublishConfig
from .playwright import PlaywrightConfig

# Map stream types to their configuration schemas
STREAM_CONFIG_SCHEMAS = {
    'playwright_link_extractor': PlaywrightConfig,
    'sitemap_news': BaseSitemapConfig,
    'sitemap_blog': BaseSitemapConfig,
    'rss_feed': RSSFeedConfig,
    'web_article': WebArticleConfig,
    'telegram_channel': TelegramConfig,
    'telegram_publish': TelegramPublishConfig,
} 