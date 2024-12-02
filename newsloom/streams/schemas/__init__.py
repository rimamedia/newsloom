from .article_searcher import ArticleSearcherConfig
from .playwright import PlaywrightConfig
from .rss import RSSConfig
from .sitemap import BaseSitemapConfig
from .telegram import TelegramConfig, TelegramPublishConfig, TelegramTestConfig
from .web_article import WebArticleConfig

STREAM_CONFIG_SCHEMAS = {
    "sitemap_news": BaseSitemapConfig,
    "sitemap_blog": BaseSitemapConfig,
    "playwright_link_extractor": PlaywrightConfig,
    "rss_feed": RSSConfig,
    "web_article": WebArticleConfig,
    "telegram_channel": TelegramConfig,
    "telegram_publish": TelegramPublishConfig,
    "telegram_test": TelegramTestConfig,
    "article_searcher": ArticleSearcherConfig,
}
