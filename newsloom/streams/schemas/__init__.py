from .playwright import PlaywrightConfig
from .rss import RSSFeedConfig
from .sitemap import BaseSitemapConfig
from .telegram import TelegramConfig, TelegramPublishConfig
from .web_article import WebArticleConfig

# Map stream types to their configuration schemas
STREAM_CONFIG_SCHEMAS = {
    "playwright_link_extractor": PlaywrightConfig,
    "sitemap_news": BaseSitemapConfig,
    "sitemap_blog": BaseSitemapConfig,
    "rss_feed": RSSFeedConfig,
    "web_article": WebArticleConfig,
    "telegram_channel": TelegramConfig,
    "telegram_publish": TelegramPublishConfig,
}
