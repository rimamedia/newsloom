from .article_searcher import ArticleSearcherConfig
from .bing_search import BingSearchConfig
from .doc_publisher import DocPublisherConfig
from .duckduckgo_search import DuckDuckGoSearchConfig
from .google_doc_creator import GoogleDocCreatorConfig
from .google_search import GoogleSearchConfig
from .news_stream import NewsStreamConfig
from .playwright import PlaywrightConfig
from .rss import RSSConfig
from .sitemap import BaseSitemapConfig
from .telegram import TelegramBulkParserConfig, TelegramConfig, TelegramPublishConfig
from .telegram_doc_publisher import TelegramDocPublisherConfig
from .web_article import WebArticleConfig

# Legacy tools - imports kept for backward compatibility

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
    "google_doc_creator": GoogleDocCreatorConfig,
    "telegram_doc_publisher": TelegramDocPublisherConfig,
    # Legacy tools removed from available schemas
    # "articlean": ArticleanConfiguration,
    # "web_scraper": WebScraperConfig,
    "duckduckgo_search": DuckDuckGoSearchConfig,
}
