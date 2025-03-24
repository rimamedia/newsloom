from datetime import timedelta
from functools import partial

from django.utils import timezone
from newsloom.celery import app

from sources.models import Source
from streams.models import Stream
from sources.services import create_news_from_links, get_news_for_send

from ._processing import stream_processing
from streams.services import (
    process_sitemap as sitemap_news_service,
    playwright_extractor,
    link_extractor,
    rss_feed_parser,
    send_news_to_telegram,
    process_telegram_channel,
telegram_doc_publisher as telegram_doc_publisher_service,
    article_searcher_extractor,
    search_bing,
    search_google,
    search_duckduckgo,
    articlean as articlean_service
)
from streams.services.news_stream import process_news_stream
from streams.services.web_scraper import web_scraper as web_scraper_service
from streams.services.google_doc_creator import google_doc_creator
from streams.services.doc_publisher import publish_docs
from streams.services.telegram_bulk_parser import run_telegram_parser


@app.task(bind=True)
@stream_processing(stream_type="sitemap_news")
def sitemap_news(self, stream: Stream) -> None:
    links = sitemap_news_service(**stream.configuration)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="sitemap_blog")
def sitemap_blog(self, stream: Stream) -> None:
    links = sitemap_news_service(**stream.configuration)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="playwright_link_extractor")
def playwright_link_extractor(self, stream: Stream) -> None:
    extractor = partial(
        link_extractor,
        url=stream.configuration['url'],
        link_selector=stream.configuration['link_selector'],
        max_links=stream.configuration['max_links'],
    )
    links = playwright_extractor(url=stream.configuration['url'], extractor=extractor)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="rss_feed")
def rss_feed(self, stream: Stream) -> None:
    links = rss_feed_parser(**stream.configuration)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="telegram_publish")
def publish_to_telegram(self, stream: Stream) -> None:
    time_threshold = timezone.now() - timedelta(minutes=stream.configuration['time_window_minutes'])
    news = get_news_for_send(
        stream, time_threshold, stream.configuration['batch_size'], stream.configuration['source_types']
    )
    if news:
        send_news_to_telegram(
            stream.configuration['channel_id'],
            stream.configuration['bot_token'],
            news,
            stream.media
        )

@app.task(bind=True)
@stream_processing(stream_type="article_searcher")
def article_searcher(self, stream: Stream) -> None:
    extractor = partial(
        article_searcher_extractor,
        url=stream.configuration['url'],
        link_selector=stream.configuration['link_selector'],
        search_text=stream.configuration['search_text'],
        article_selector=stream.configuration['article_selector'],
        link_selector_type=stream.configuration['link_selector_type'],
        article_selector_type=stream.configuration['article_selector_type'],
        max_links=stream.configuration['max_links'],
    )
    links = playwright_extractor(url=stream.configuration['url'], extractor=extractor)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="bing_search")
def bing_search(self, stream: Stream) -> None:
    links = search_bing(**stream.configuration)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="google_search")
def google_search(self, stream: Stream) -> None:
    links = search_google(**stream.configuration)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="duckduckgo_search")
def duckduckgo_search(self, stream: Stream) -> None:
    links = search_duckduckgo(**stream.configuration)
    create_news_from_links(stream.source, links)


@app.task(bind=True)
@stream_processing(stream_type="telegram_bulk_parser")
def telegram_bulk_parser(self, stream: Stream) -> None:
    run_telegram_parser(stream.id, **stream.configuration)


@app.task(bind=True)
@stream_processing(stream_type="news_stream")
def news_stream(self, stream: Stream) -> None:
    process_news_stream(stream.id, **stream.configuration)



@app.task(bind=True)
@stream_processing(stream_type="doc_publisher")
def doc_publisher(self, stream: Stream) -> None:
    publish_docs(stream, **stream.configuration)


@app.task(bind=True)
@stream_processing(stream_type="google_doc_creator")
def google_doc_creator(self, stream: Stream) -> None:
    google_doc_creator(stream, **stream.configuration)


@app.task(bind=True)
@stream_processing(stream_type="telegram_doc_publisher")
def telegram_doc_publisher(self, stream: Stream) -> None:
    telegram_doc_publisher_service(stream, **stream.configuration)


@app.task(bind=True)
@stream_processing(stream_type="articlean")
def articlean(self, stream: Stream) -> None:
    articlean_service(stream.id, **stream.configuration)


@app.task(bind=True)
@stream_processing(stream_type="web_scraper")
def web_scraper(self, stream: Stream) -> None:
    web_scraper_service(stream.id, **stream.configuration)


@app.task(bind=True)
@stream_processing
def dummy(self, *args, **kwargs) -> None:
   raise Exception("Dummy task")


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



# Map stream types to their corresponding task functions
# TODO: add llm rewrite task
TASK_MAPPING = {
    "sitemap_news": sitemap_news,
    "sitemap_blog": sitemap_blog,
    "playwright_link_extractor": playwright_link_extractor,
    "rss_feed": rss_feed,
    "telegram_publish": publish_to_telegram,
    "article_searcher": article_searcher,
    "bing_search": bing_search,
    "google_search": google_search,
    "duckduckgo_search": duckduckgo_search,
    "telegram_bulk_parser": telegram_bulk_parser,
    "news_stream": news_stream,
    "doc_publisher": doc_publisher,
    "google_doc_creator": google_doc_creator,
    "telegram_doc_publisher": telegram_doc_publisher,
    "articlean": articlean,
    "web_scraper": web_scraper,

    "web_article": dummy,
    "telegram_channel": dummy,
}