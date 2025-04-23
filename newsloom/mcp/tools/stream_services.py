"""
MCP stream services tool implementations for Newsloom.

This module provides MCP tool implementations for executing stream services directly.
"""

import json
import logging

# Import Django models
from streams.models import Stream
from agents.models import Agent

# Import MCP types
try:
    from mcp.types import ErrorCode, McpError

    MCP_AVAILABLE = True
except ImportError:
    # Mock implementations for development without MCP SDK
    class ErrorCode:
        InvalidRequest = "InvalidRequest"
        MethodNotFound = "MethodNotFound"
        InvalidParams = "InvalidParams"
        InternalError = "InternalError"

    class McpError(Exception):
        def __init__(self, code, message):
            self.code = code
            self.message = message
            super().__init__(f"{code}: {message}")

    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


def register_stream_services_tools(server):
    """
    Register stream services tools with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock stream services tools")
        return

    @server.tool(
        name="execute_news_stream",
        description="Process news items using the specified agent",
        input_schema={
            "type": "object",
            "properties": {
                "stream_id": {
                    "type": "integer",
                    "description": "ID of the stream",
                },
                "agent_id": {
                    "type": "integer",
                    "description": "ID of the agent to use",
                },
                "time_window_minutes": {
                    "type": "integer",
                    "description": "Time window in minutes to look back for news (default: 60)",
                },
                "max_items": {
                    "type": "integer",
                    "description": "Maximum number of news items to process (default: 100)",
                },
                "save_to_docs": {
                    "type": "boolean",
                    "description": "Whether to save the processed output to docs (default: true)",
                },
            },
            "required": ["stream_id", "agent_id"],
        },
    )
    async def execute_news_stream(request):
        """
        Process news items using the specified agent.

        Args:
            request: The MCP request object containing:
                stream_id: ID of the stream
                agent_id: ID of the agent to use
                time_window_minutes: Time window in minutes to look back for news
                max_items: Maximum number of news items to process
                save_to_docs: Whether to save the processed output to docs

        Returns:
            Dict containing processing results
        """
        try:
            args = request.params.arguments
            stream_id = args.get("stream_id")
            agent_id = args.get("agent_id")
            time_window_minutes = args.get("time_window_minutes", 60)
            max_items = args.get("max_items", 100)
            save_to_docs = args.get("save_to_docs", True)

            # Validate stream_id
            try:
                # Using _ to indicate intentionally unused variable
                _ = Stream.objects.get(id=stream_id)
            except Stream.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Stream with id {stream_id} does not exist",
                )

            # Validate agent_id
            try:
                agent = Agent.objects.get(id=agent_id)
                if not agent.is_active:
                    raise McpError(
                        ErrorCode.InvalidParams,
                        f"Agent with id {agent_id} is not active",
                    )
            except Agent.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Agent with id {agent_id} does not exist",
                )

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

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing news_stream: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error executing news_stream: {str(e)}"
            )

    @server.tool(
        name="execute_web_scraper",
        description="Scrape content for news articles with empty text",
        input_schema={
            "type": "object",
            "properties": {
                "stream_id": {
                    "type": "integer",
                    "description": "ID of the stream",
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Number of news articles to process in each batch (default: 10)",
                },
            },
            "required": ["stream_id"],
        },
    )
    async def execute_web_scraper(request):
        """
        Scrape content for news articles with empty text.

        Args:
            request: The MCP request object containing:
                stream_id: ID of the stream
                batch_size: Number of news articles to process in each batch

        Returns:
            Dict containing task execution results
        """
        try:
            args = request.params.arguments
            stream_id = args.get("stream_id")
            batch_size = args.get("batch_size", 10)

            # Validate stream_id
            try:
                # Using _ to indicate intentionally unused variable
                _ = Stream.objects.get(id=stream_id)
            except Stream.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Stream with id {stream_id} does not exist",
                )

            # Import the service function
            from streams.services.web_scraper import web_scraper

            # Execute the service
            result = web_scraper(
                stream_id=stream_id,
                batch_size=batch_size,
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing web_scraper: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error executing web_scraper: {str(e)}"
            )

    @server.tool(
        name="execute_doc_publisher",
        description="Publish docs from database to Telegram channel",
        input_schema={
            "type": "object",
            "properties": {
                "stream_id": {
                    "type": "integer",
                    "description": "ID of the stream",
                },
                "channel_id": {
                    "type": "string",
                    "description": "Telegram channel ID",
                },
                "bot_token": {
                    "type": "string",
                    "description": "Telegram bot token",
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Maximum number of docs to process (default: 10)",
                },
                "google_doc_links": {
                    "type": "boolean",
                    "description": "Whether to include Google Doc links in messages "
                    "(default: false)",
                },
            },
            "required": ["stream_id", "channel_id", "bot_token"],
        },
    )
    async def execute_doc_publisher(request):
        """
        Publish docs from database to Telegram channel.

        Args:
            request: The MCP request object containing:
                stream_id: ID of the stream
                channel_id: Telegram channel ID
                bot_token: Telegram bot token
                batch_size: Maximum number of docs to process
                google_doc_links: Whether to include Google Doc links in messages

        Returns:
            Dict containing task execution results
        """
        try:
            args = request.params.arguments
            stream_id = args.get("stream_id")
            channel_id = args.get("channel_id")
            bot_token = args.get("bot_token")
            batch_size = args.get("batch_size", 10)
            google_doc_links = args.get("google_doc_links", False)

            # Validate stream_id
            try:
                stream = Stream.objects.get(id=stream_id)
                if not stream.media:
                    raise McpError(
                        ErrorCode.InvalidParams,
                        f"Stream with id {stream_id} must have an associated media",
                    )
            except Stream.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Stream with id {stream_id} does not exist",
                )

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
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": True,
                                "message": (
                                    f"Successfully published docs to Telegram channel {channel_id}"
                                ),
                            },
                            indent=2,
                        ),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing doc_publisher: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error executing doc_publisher: {str(e)}"
            )

    @server.tool(
        name="execute_google_doc_creator",
        description="Create Google Docs for documents in the database",
        input_schema={
            "type": "object",
            "properties": {
                "stream_id": {
                    "type": "integer",
                    "description": "ID of the stream",
                },
                "folder_id": {
                    "type": "string",
                    "description": "Google Drive folder ID",
                },
                "template_id": {
                    "type": "string",
                    "description": "Optional: Google Doc template ID",
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Maximum number of docs to process (default: 10)",
                },
            },
            "required": ["stream_id", "folder_id"],
        },
    )
    async def execute_google_doc_creator(request):
        """
        Create Google Docs for documents in the database.

        Args:
            request: The MCP request object containing:
                stream_id: ID of the stream
                folder_id: Google Drive folder ID
                template_id: Optional Google Doc template ID
                batch_size: Maximum number of docs to process

        Returns:
            Dict containing task execution results
        """
        try:
            args = request.params.arguments
            stream_id = args.get("stream_id")
            folder_id = args.get("folder_id")
            template_id = args.get("template_id")
            batch_size = args.get("batch_size", 10)

            # Validate stream_id
            try:
                stream = Stream.objects.get(id=stream_id)
                if not stream.media:
                    raise McpError(
                        ErrorCode.InvalidParams,
                        f"Stream with id {stream_id} must have an associated media",
                    )
            except Stream.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Stream with id {stream_id} does not exist",
                )

            # Import the service function
            from streams.services.google_doc_creator import google_doc_creator

            # Execute the service
            result = google_doc_creator(
                stream=stream,
                folder_id=folder_id,
                template_id=template_id,
                batch_size=batch_size,
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing google_doc_creator: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error executing google_doc_creator: {str(e)}"
            )

    @server.tool(
        name="execute_telegram_bulk_parser",
        description="Parse Telegram channels for content",
        input_schema={
            "type": "object",
            "properties": {
                "stream_id": {
                    "type": "integer",
                    "description": "ID of the stream",
                },
                "time_window_minutes": {
                    "type": "integer",
                    "description": "Time window in minutes to look back (default: 120)",
                },
                "max_scrolls": {
                    "type": "integer",
                    "description": "Maximum number of scrolls (default: 50)",
                },
                "wait_time": {
                    "type": "integer",
                    "description": "Wait time between scrolls in seconds (default: 5)",
                },
            },
            "required": ["stream_id"],
        },
    )
    async def execute_telegram_bulk_parser(request):
        """
        Parse Telegram channels for content.

        Args:
            request: The MCP request object containing:
                stream_id: ID of the stream
                time_window_minutes: Time window in minutes to look back
                max_scrolls: Maximum number of scrolls
                wait_time: Wait time between scrolls in seconds

        Returns:
            Dict containing task execution results
        """
        try:
            args = request.params.arguments
            stream_id = args.get("stream_id")
            time_window_minutes = args.get("time_window_minutes", 120)
            max_scrolls = args.get("max_scrolls", 50)
            wait_time = args.get("wait_time", 5)

            # Validate stream_id
            try:
                # Using _ to indicate intentionally unused variable
                _ = Stream.objects.get(id=stream_id)
            except Stream.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Stream with id {stream_id} does not exist",
                )

            # Import the service function
            from streams.services.telegram_bulk_parser import run_telegram_parser

            # Execute the service
            result = run_telegram_parser(
                stream_id=stream_id,
                time_window_minutes=time_window_minutes,
                max_scrolls=max_scrolls,
                wait_time=wait_time,
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing telegram_bulk_parser: {str(e)}")
            raise McpError(
                ErrorCode.InternalError,
                f"Error executing telegram_bulk_parser: {str(e)}",
            )

    @server.tool(
        name="execute_link_parser",
        description="Enrich links with content using web scraping",
        input_schema={
            "type": "object",
            "properties": {
                "links": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to enrich with content",
                },
            },
            "required": ["links"],
        },
    )
    async def execute_link_parser(request):
        """
        Enrich links with content using web scraping.

        Args:
            request: The MCP request object containing:
                links: List of URLs to enrich with content

        Returns:
            Dict containing enriched links with content
        """
        try:
            args = request.params.arguments
            links = args.get("links", [])

            if not links:
                raise McpError(
                    ErrorCode.InvalidParams,
                    "No links provided for enrichment",
                )

            # Import the service function
            from streams.services.link_parser import enrich_links

            # Execute the service
            result = enrich_links(links)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing link_parser: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error executing link_parser: {str(e)}"
            )

    @server.tool(
        name="execute_sitemap_parser",
        description="Extract links from a sitemap URL",
        input_schema={
            "type": "object",
            "properties": {
                "sitemap_url": {
                    "type": "string",
                    "description": "URL of the sitemap to parse",
                },
                "max_links": {
                    "type": "integer",
                    "description": "Maximum number of links to extract (default: 100)",
                },
                "follow_next": {
                    "type": "boolean",
                    "description": "Whether to follow next page links (default: false)",
                },
            },
            "required": ["sitemap_url"],
        },
    )
    async def execute_sitemap_parser(request):
        """
        Extract links from a sitemap URL.

        Args:
            request: The MCP request object containing:
                sitemap_url: URL of the sitemap to parse
                max_links: Maximum number of links to extract
                follow_next: Whether to follow next page links

        Returns:
            Dict containing extracted links
        """
        try:
            args = request.params.arguments
            sitemap_url = args.get("sitemap_url")
            max_links = args.get("max_links", 100)
            follow_next = args.get("follow_next", False)

            # Import the service function
            from streams.services import process_sitemap

            # Execute the service
            result = process_sitemap(
                sitemap_url=sitemap_url,
                max_links=max_links,
                follow_next=follow_next,
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "links": result,
                                "count": len(result),
                            },
                            indent=2,
                        ),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing sitemap_parser: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error executing sitemap_parser: {str(e)}"
            )

    @server.tool(
        name="execute_rss_parser",
        description="Extract links from an RSS feed URL",
        input_schema={
            "type": "object",
            "properties": {
                "feed_url": {
                    "type": "string",
                    "description": "URL of the RSS feed to parse",
                },
                "max_entries": {
                    "type": "integer",
                    "description": "Maximum number of entries to extract (default: 100)",
                },
            },
            "required": ["feed_url"],
        },
    )
    async def execute_rss_parser(request):
        """
        Extract links from an RSS feed URL.

        Args:
            request: The MCP request object containing:
                feed_url: URL of the RSS feed to parse
                max_entries: Maximum number of entries to extract

        Returns:
            Dict containing extracted links
        """
        try:
            args = request.params.arguments
            feed_url = args.get("feed_url")
            max_entries = args.get("max_entries", 100)

            # Import the service function
            from streams.services import rss_feed_parser

            # Execute the service
            result = rss_feed_parser(
                feed_url=feed_url,
                max_entries=max_entries,
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "links": result,
                                "count": len(result),
                            },
                            indent=2,
                        ),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing rss_parser: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error executing rss_parser: {str(e)}"
            )

    @server.tool(
        name="execute_playwright_extractor",
        description="Extract links from a webpage using Playwright",
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to extract links from",
                },
                "link_selector": {
                    "type": "string",
                    "description": "CSS selector for links",
                },
                "max_links": {
                    "type": "integer",
                    "description": "Maximum number of links to extract (default: 100)",
                },
            },
            "required": ["url", "link_selector"],
        },
    )
    async def execute_playwright_extractor(request):
        """
        Extract links from a webpage using Playwright.

        Args:
            request: The MCP request object containing:
                url: URL of the webpage to extract links from
                link_selector: CSS selector for links
                max_links: Maximum number of links to extract

        Returns:
            Dict containing extracted links
        """
        try:
            args = request.params.arguments
            url = args.get("url")
            link_selector = args.get("link_selector")
            max_links = args.get("max_links", 100)

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
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "links": result,
                                "count": len(result),
                            },
                            indent=2,
                        ),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing playwright_extractor: {str(e)}")
            raise McpError(
                ErrorCode.InternalError,
                f"Error executing playwright_extractor: {str(e)}",
            )

    @server.tool(
        name="execute_search_engine",
        description="Search for content using various search engines",
        input_schema={
            "type": "object",
            "properties": {
                "engine": {
                    "type": "string",
                    "enum": ["google", "bing", "duckduckgo"],
                    "description": "Search engine to use",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search for",
                },
                "max_results_per_keyword": {
                    "type": "integer",
                    "description": "Maximum number of results per keyword (default: 5)",
                },
                "search_type": {
                    "type": "string",
                    "enum": ["news", "web"],
                    "description": "Type of search to perform (default: news)",
                },
                "days_ago": {
                    "type": "integer",
                    "description": "For Google: Number of days to look back (default: 7)",
                },
                "region": {
                    "type": "string",
                    "description": "For DuckDuckGo: Region code (default: wt-wt)",
                },
                "time_range": {
                    "type": "string",
                    "enum": ["d", "w", "m"],
                    "description": "For DuckDuckGo: Time range (d=day, w=week, m=month) "
                    "(default: d)",
                },
            },
            "required": ["engine", "keywords"],
        },
    )
    async def execute_search_engine(request):
        """
        Search for content using various search engines.

        Args:
            request: The MCP request object containing:
                engine: Search engine to use (google, bing, duckduckgo)
                keywords: Keywords to search for
                max_results_per_keyword: Maximum number of results per keyword
                search_type: Type of search to perform (news, web)
                days_ago: For Google: Number of days to look back
                region: For DuckDuckGo: Region code
                time_range: For DuckDuckGo: Time range (d=day, w=week, m=month)

        Returns:
            Dict containing search results
        """
        try:
            args = request.params.arguments
            engine = args.get("engine")
            keywords = args.get("keywords", [])
            max_results = args.get("max_results_per_keyword", 5)
            search_type = args.get("search_type", "news")
            days_ago = args.get("days_ago", 7)
            region = args.get("region", "wt-wt")
            time_range = args.get("time_range", "d")

            if not keywords:
                raise McpError(
                    ErrorCode.InvalidParams,
                    "No keywords provided for search",
                )

            # Import the appropriate search function based on engine
            if engine == "google":
                from streams.services import search_google

                result = search_google(
                    keywords=keywords,
                    max_results_per_keyword=max_results,
                    days_ago=days_ago,
                    search_type=search_type,
                )
            elif engine == "bing":
                from streams.services import search_bing

                result = search_bing(
                    keywords=keywords,
                    max_results_per_keyword=max_results,
                    search_type=search_type,
                )
            elif engine == "duckduckgo":
                from streams.services import search_duckduckgo

                # Convert keywords array to string for DuckDuckGo
                keywords_str = " ".join(keywords)
                result = search_duckduckgo(
                    keywords=keywords_str,
                    max_results=max_results * len(keywords),
                    region=region,
                    time_range=time_range,
                )
            else:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Unsupported search engine: {engine}",
                )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "engine": engine,
                                "links": result,
                                "count": len(result),
                            },
                            indent=2,
                        ),
                    }
                ]
            }
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error executing search_engine: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error executing search_engine: {str(e)}"
            )
