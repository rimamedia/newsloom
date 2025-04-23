"""Functions implementing stream service operations through Claude API."""

import logging
from typing import Dict, List, Optional, Any

from streams.models import Stream
from agents.models import Agent

logger = logging.getLogger(__name__)


def execute_news_stream(
    stream_id: int,
    agent_id: int,
    time_window_minutes: int = 60,
    max_items: int = 100,
    save_to_docs: bool = True,
) -> Dict[str, Any]:
    """
    Process news items using the specified agent.

    Args:
        stream_id: ID of the stream
        agent_id: ID of the agent to use
        time_window_minutes: Time window in minutes to look back for news (default: 60)
        max_items: Maximum number of news items to process (default: 100)
        save_to_docs: Whether to save the processed output to docs (default: true)

    Returns:
        Dict containing processing results

    Raises:
        Stream.DoesNotExist: If stream with given id doesn't exist
        Agent.DoesNotExist: If agent with given id doesn't exist
        ValueError: If agent is not active
    """
    # Validate stream_id
    try:
        # Using _ to indicate intentionally unused variable
        _ = Stream.objects.get(id=stream_id)
    except Stream.DoesNotExist:
        raise Stream.DoesNotExist(f"Stream with id {stream_id} does not exist")

    # Validate agent_id
    try:
        agent = Agent.objects.get(id=agent_id)
        if not agent.is_active:
            raise ValueError(f"Agent with id {agent_id} is not active")
    except Agent.DoesNotExist:
        raise Agent.DoesNotExist(f"Agent with id {agent_id} does not exist")

    # Import the service function
    from streams.services.news_stream import process_news_stream

    # Execute the service
    result = process_news_stream(
        stream_id=stream_id,
        agent_id=agent_id,
        time_window_minutes=time_window_minutes,
        max_items=max_items,
        save_to_docs=save_to_docs,
    )

    return result


def execute_web_scraper(
    stream_id: int,
    batch_size: int = 10,
) -> Dict[str, Any]:
    """
    Scrape content for news articles with empty text.

    Args:
        stream_id: ID of the stream
        batch_size: Number of news articles to process in each batch (default: 10)

    Returns:
        Dict containing task execution results

    Raises:
        Stream.DoesNotExist: If stream with given id doesn't exist
    """
    # Validate stream_id
    try:
        # Using _ to indicate intentionally unused variable
        _ = Stream.objects.get(id=stream_id)
    except Stream.DoesNotExist:
        raise Stream.DoesNotExist(f"Stream with id {stream_id} does not exist")

    # Import the service function
    from streams.services.web_scraper import web_scraper

    # Execute the service
    result = web_scraper(
        stream_id=stream_id,
        batch_size=batch_size,
    )

    return result


def execute_doc_publisher(
    stream_id: int,
    channel_id: str,
    bot_token: str,
    batch_size: int = 10,
    google_doc_links: bool = False,
) -> Dict[str, Any]:
    """
    Publish docs from database to Telegram channel.

    Args:
        stream_id: ID of the stream
        channel_id: Telegram channel ID
        bot_token: Telegram bot token
        batch_size: Maximum number of docs to process (default: 10)
        google_doc_links: Whether to include Google Doc links in messages (default: false)

    Returns:
        Dict containing task execution results

    Raises:
        Stream.DoesNotExist: If stream with given id doesn't exist
        ValueError: If stream doesn't have an associated media
    """
    # Validate stream_id
    try:
        stream = Stream.objects.get(id=stream_id)
        if not stream.media:
            raise ValueError(
                f"Stream with id {stream_id} must have an associated media"
            )
    except Stream.DoesNotExist:
        raise Stream.DoesNotExist(f"Stream with id {stream_id} does not exist")

    # Import the service function
    from streams.services.doc_publisher import publish_docs

    # Execute the service
    # Using _ to indicate intentionally unused variable
    _ = publish_docs(
        stream=stream,
        channel_id=channel_id,
        bot_token=bot_token,
        batch_size=batch_size,
        google_doc_links=google_doc_links,
    )

    return {
        "success": True,
        "message": f"Successfully published docs to Telegram channel {channel_id}",
    }


def execute_google_doc_creator(
    stream_id: int,
    folder_id: str,
    template_id: Optional[str] = None,
    batch_size: int = 10,
) -> Dict[str, Any]:
    """
    Create Google Docs for documents in the database.

    Args:
        stream_id: ID of the stream
        folder_id: Google Drive folder ID
        template_id: Optional Google Doc template ID
        batch_size: Maximum number of docs to process (default: 10)

    Returns:
        Dict containing task execution results

    Raises:
        Stream.DoesNotExist: If stream with given id doesn't exist
        ValueError: If stream doesn't have an associated media
    """
    # Validate stream_id
    try:
        stream = Stream.objects.get(id=stream_id)
        if not stream.media:
            raise ValueError(
                f"Stream with id {stream_id} must have an associated media"
            )
    except Stream.DoesNotExist:
        raise Stream.DoesNotExist(f"Stream with id {stream_id} does not exist")

    # Import the service function
    from streams.services.google_doc_creator import google_doc_creator

    # Execute the service
    result = google_doc_creator(
        stream=stream,
        folder_id=folder_id,
        template_id=template_id,
        batch_size=batch_size,
    )

    return result


def execute_telegram_bulk_parser(
    stream_id: int,
    time_window_minutes: int = 120,
    max_scrolls: int = 50,
    wait_time: int = 5,
) -> Dict[str, Any]:
    """
    Parse Telegram channels for content.

    Args:
        stream_id: ID of the stream
        time_window_minutes: Time window in minutes to look back (default: 120)
        max_scrolls: Maximum number of scrolls (default: 50)
        wait_time: Wait time between scrolls in seconds (default: 5)

    Returns:
        Dict containing task execution results

    Raises:
        Stream.DoesNotExist: If stream with given id doesn't exist
    """
    # Validate stream_id
    try:
        # Using _ to indicate intentionally unused variable
        _ = Stream.objects.get(id=stream_id)
    except Stream.DoesNotExist:
        raise Stream.DoesNotExist(f"Stream with id {stream_id} does not exist")

    # Import the service function
    from streams.services.telegram_bulk_parser import run_telegram_parser

    # Execute the service
    result = run_telegram_parser(
        stream_id=stream_id,
        time_window_minutes=time_window_minutes,
        max_scrolls=max_scrolls,
        wait_time=wait_time,
    )

    return result


def execute_link_parser(
    links: List[str],
) -> Dict[str, Any]:
    """
    Enrich links with content using web scraping.

    Args:
        links: List of URLs to enrich with content

    Returns:
        Dict containing enriched links with content

    Raises:
        ValueError: If no links are provided
    """
    if not links:
        raise ValueError("No links provided for enrichment")

    # Import the service function
    from streams.services.link_parser import enrich_links

    # Execute the service
    result = enrich_links(links)

    return result


def execute_sitemap_parser(
    sitemap_url: str,
    max_links: int = 100,
    follow_next: bool = False,
) -> Dict[str, Any]:
    """
    Extract links from a sitemap URL.

    Args:
        sitemap_url: URL of the sitemap to parse
        max_links: Maximum number of links to extract (default: 100)
        follow_next: Whether to follow next page links (default: false)

    Returns:
        Dict containing extracted links
    """
    # Import the service function
    from streams.services import process_sitemap

    # Execute the service
    result = process_sitemap(
        sitemap_url=sitemap_url,
        max_links=max_links,
        follow_next=follow_next,
    )

    return {
        "links": result,
        "count": len(result),
    }


def execute_rss_parser(
    feed_url: str,
    max_entries: int = 100,
) -> Dict[str, Any]:
    """
    Extract links from an RSS feed URL.

    Args:
        feed_url: URL of the RSS feed to parse
        max_entries: Maximum number of entries to extract (default: 100)

    Returns:
        Dict containing extracted links
    """
    # Import the service function
    from streams.services import rss_feed_parser

    # Execute the service
    result = rss_feed_parser(
        feed_url=feed_url,
        max_entries=max_entries,
    )

    return {
        "links": result,
        "count": len(result),
    }


def execute_playwright_extractor(
    url: str,
    link_selector: str,
    max_links: int = 100,
) -> Dict[str, Any]:
    """
    Extract links from a webpage using Playwright.

    Args:
        url: URL of the webpage to extract links from
        link_selector: CSS selector for links
        max_links: Maximum number of links to extract (default: 100)

    Returns:
        Dict containing extracted links
    """
    # Import the service functions
    from streams.services import playwright_extractor, link_extractor
    from functools import partial

    # Create extractor function
    extractor = partial(
        link_extractor,
        url=url,
        link_selector=link_selector,
        max_links=max_links,
    )

    # Execute the service
    result = playwright_extractor(
        url=url,
        extractor=extractor,
    )

    return {
        "links": result,
        "count": len(result),
    }


def execute_search_engine(
    engine: str,
    keywords: List[str],
    max_results_per_keyword: int = 5,
    search_type: str = "news",
    days_ago: int = 7,
    region: str = "wt-wt",
    time_range: str = "d",
) -> Dict[str, Any]:
    """
    Search for content using various search engines.

    Args:
        engine: Search engine to use (google, bing, duckduckgo)
        keywords: Keywords to search for
        max_results_per_keyword: Maximum number of results per keyword (default: 5)
        search_type: Type of search to perform (news, web) (default: news)
        days_ago: For Google: Number of days to look back (default: 7)
        region: For DuckDuckGo: Region code (default: wt-wt)
        time_range: For DuckDuckGo: Time range (d=day, w=week, m=month) (default: d)

    Returns:
        Dict containing search results

    Raises:
        ValueError: If no keywords are provided or if an unsupported search engine is specified
    """
    if not keywords:
        raise ValueError("No keywords provided for search")

    # Import the appropriate search function based on engine
    if engine == "google":
        from streams.services import search_google

        result = search_google(
            keywords=keywords,
            max_results_per_keyword=max_results_per_keyword,
            days_ago=days_ago,
            search_type=search_type,
        )
    elif engine == "bing":
        from streams.services import search_bing

        result = search_bing(
            keywords=keywords,
            max_results_per_keyword=max_results_per_keyword,
            search_type=search_type,
        )
    elif engine == "duckduckgo":
        from streams.services import search_duckduckgo

        # Convert keywords array to string for DuckDuckGo
        keywords_str = " ".join(keywords)
        result = search_duckduckgo(
            keywords=keywords_str,
            max_results=max_results_per_keyword * len(keywords),
            region=region,
            time_range=time_range,
        )
    else:
        raise ValueError(f"Unsupported search engine: {engine}")

    return {
        "engine": engine,
        "links": result,
        "count": len(result),
    }
