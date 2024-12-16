import logging

from .article_searcher import search_articles
from .bing_search import search_bing
from .doc_publisher import publish_docs
from .news_stream import process_news_stream
from .playwright import extract_links
from .rss import parse_rss_feed
from .sitemap import parse_sitemap
from .telegram import monitor_telegram_channel
from .telegram_bulk_parser import run_telegram_parser
from .telegram_publisher import publish_to_telegram
from .telegram_test import test_telegram_channel
from .web import scrape_web_article

# Map stream types to their corresponding task functions
# TODO: add llm rewrite task
TASK_MAPPING = {
    "sitemap_news": parse_sitemap,
    "sitemap_blog": parse_sitemap,
    "playwright_link_extractor": extract_links,
    "rss_feed": parse_rss_feed,
    "web_article": scrape_web_article,
    "telegram_channel": monitor_telegram_channel,
    "telegram_publish": publish_to_telegram,
    "telegram_test": test_telegram_channel,
    "article_searcher": search_articles,
    "bing_search": search_bing,
    "telegram_bulk_parser": run_telegram_parser,
    "news_stream": process_news_stream,
    "doc_publisher": publish_docs,
}


def get_task_function(stream_type):
    """Get the appropriate task function for a given stream type."""
    logger = logging.getLogger(__name__)

    logger.debug(f"Looking for task function for stream_type: '{stream_type}'")
    logger.debug(f"Available task mappings: {list(TASK_MAPPING.keys())}")

    task_function = TASK_MAPPING.get(stream_type)

    if task_function is None:
        logger.error(f"No task function found for stream_type: '{stream_type}'")
        logger.error(f"Type of stream_type: {type(stream_type)}")
    else:
        logger.debug(f"Found task function: {task_function.__name__}")

    return task_function


# Example configuration for each task type
TASK_CONFIG_EXAMPLES = {
    "sitemap_news": {
        "sitemap_url": "https://example.com/sitemap.xml",
        "max_links": 100,
        "follow_next": False,
    },
    "sitemap_blog": {
        "sitemap_url": "https://example.com/blog-sitemap.xml",
        "max_links": 100,
        "follow_next": False,
    },
    "playwright_link_extractor": {
        "url": "https://example.com",
        "link_selector": "a.article-link",
        "max_links": 100,
    },
    "rss_feed": {
        "feed_url": "https://example.com/feed.xml",
        "max_entries": 100,
    },
    "web_article": {
        "base_url": "https://example.com",
        "selectors": {
            "title": "h1.article-title",
            "content": "div.article-content",
            "date": "time.published-date",
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    },
    "telegram_channel": {
        "posts_limit": 20,
    },
    "telegram_publish": {
        "channel_id": "-100123456789",
        "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        "batch_size": 10,
        "time_window_minutes": 10,
    },
    "telegram_test": {
        "channel_id": "-100123456789",
        "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
    },
    "article_searcher": {
        "url": "https://example.com",
        "link_selector": "//*[@id='wtxt']/div[2]/ul/li[1]/a",
        "link_selector_type": "xpath",
        "article_selector": "div.article-content",
        "article_selector_type": "css",
        "search_text": "białoruś",
        "max_links": 10,
    },
    "bing_search": {
        "keywords": ["climate change", "renewable energy"],
        "max_results_per_keyword": 5,
        "search_type": "news",
        "debug": False,
    },
    "telegram_bulk_parser": {
        "time_window_minutes": 120,  # 2 hours window
        "max_scrolls": 50,  # Scroll up to 50 times
        "wait_time": 5,  # Wait 5 seconds between scrolls
    },
    "news_stream": {
        "agent_id": 1,  # ID of the agent to use
        "time_window_minutes": 60,  # Look back 1 hour
        "max_items": 100,  # Process up to 100 news items
        "save_to_docs": True,  # Save processed output to docs
    },
    "doc_publisher": {
        "channel_id": "-100123456789",  # Telegram channel ID
        "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",  # Telegram bot token
        "time_window_minutes": 60,  # Look back 1 hour
        "batch_size": 10,  # Process up to 10 docs at a time
    },
}


def get_task_config_example(stream_type):
    """Get the example configuration for a given stream type."""
    return TASK_CONFIG_EXAMPLES.get(stream_type, {})
