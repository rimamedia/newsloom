
from typing import Any

from newsloom.celery import app


from streams.models import Stream
from sources.services import create_news_from_links

from ._processing import stream_processing
from streams.services import (
    process_sitemap as sitemap_news_service,
    playwright_extract_links,
)

@app.task(bind=True)
@stream_processing(stream_type="sitemap_news")
def sitemap_news(self, stream: Stream) -> None:
    links = sitemap_news_service(**stream.configuration)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="sitemap_blog")
def sitemap_blog(self, stream: Stream) -> dict[str, Any]:
    links = sitemap_news_service(stream, **stream.configuration)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="playwright_link_extractor")
def playwright_link_extractor(self, stream: Stream) -> None:
    links = playwright_extract_links(**stream.configuration)
    create_news_from_links(stream.source, links)


# Example configuration for each task type
TASK_CONFIG_EXAMPLES = {
    "articlean": {
        "endpoint": "http://35.92.156.236/process-url",
        "token": "your-api-key-here",
    },
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
        "source_types": ["web", "telegram"],  # Optional: filter news by source types
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
    "google_search": {
        "keywords": ["climate change", "renewable energy"],
        "max_results_per_keyword": 5,
        "days_ago": 7,
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
    "google_doc_creator": {
        "folder_id": "1a2b3c4d5e6f7g8h9i0j",  # Google Drive folder ID (found in folder URL)
        "template_id": "1xYz2wVu3tSr4qPn5mL6k",  # Optional: Google Doc template ID (found in template doc URL) # noqa E501
    },
    "telegram_doc_publisher": {
        "message_template": "{title}\n\n{google_doc_link}",  # Message template
        "batch_size": 10,  # Process up to 10 docs at a time
        "delay_between_messages": 2,  # Delay between messages in seconds
    },
    "web_scraper": {
        "batch_size": 10,  # Process 10 empty news articles at a time
    },
    "duckduckgo_search": {
        "keywords": "artificial intelligence news",
        "max_results": 10,
        "region": "wt-wt",
        "time_range": "d",
        "safesearch": "moderate",
    },
}


def get_task_config_example(stream_type):
    """Get the example configuration for a given stream type."""
    return TASK_CONFIG_EXAMPLES.get(stream_type, {})


# TODO: add name conventions for tasks

# from ._process import process_stream



import logging

# Map stream types to their corresponding task functions
# TODO: add llm rewrite task
# TASK_MAPPING = {
#     "sitemap_news": parse_sitemap,
#     "sitemap_blog": parse_sitemap,
#     "playwright_link_extractor": extract_links,

#     "rss_feed": parse_rss_feed,
#     "web_article": scrape_web_article,
#     "telegram_channel": monitor_telegram_channel,
#     "telegram_publish": publish_to_telegram,
#     "article_searcher": search_articles,
#     "bing_search": search_bing,
#     "google_search": search_google,
#     "telegram_bulk_parser": run_telegram_parser,
#     "news_stream": process_news_stream,
#     "doc_publisher": publish_docs,
#     "google_doc_creator": google_doc_creator,
#     "telegram_doc_publisher": telegram_doc_publisher,
#     "articlean": articlean,
#     "web_scraper": web_scraper,
#     "duckduckgo_search": duckduckgo_search,
# }