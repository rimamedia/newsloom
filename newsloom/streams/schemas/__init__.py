from pydantic import BaseModel

from .article_searcher import ArticleSearcherConfig
from .articlean import ArticleanConfiguration
from .bing_search import BingSearchConfig
from .doc_publisher import DocPublisherConfig
from .google_search import GoogleSearchConfig
from .news_stream import NewsStreamConfig
from .playwright import PlaywrightConfig
from .rss import RSSConfig
from .sitemap import BaseSitemapConfig
from .telegram import TelegramBulkParserConfig, TelegramConfig, TelegramPublishConfig
from .web_article import WebArticleConfig


class BaseConfig(BaseModel):
    """Base configuration class for all stream configurations.

    This class sets up common configuration for all stream schemas,
    including allowing extra fields to be provided without validation errors.
    """

    model_config = {"extra": "ignore"}  # Allow but ignore any extra fields


STREAM_CONFIG_SCHEMAS = {
    "sitemap_news": BaseSitemapConfig,
    "sitemap_blog": BaseSitemapConfig,
    "playwright_link_extractor": PlaywrightConfig,
    "rss_feed": RSSConfig,
    "web_article": WebArticleConfig,
    "telegram_channel": TelegramConfig,
    "telegram_publish": TelegramPublishConfig,
    "telegram_bulk_parser": TelegramBulkParserConfig,
    "article_searcher": ArticleSearcherConfig,
    "bing_search": BingSearchConfig,
    "google_search": GoogleSearchConfig,
    "news_stream": NewsStreamConfig,
    "doc_publisher": DocPublisherConfig,
    "articlean": ArticleanConfiguration,
}
