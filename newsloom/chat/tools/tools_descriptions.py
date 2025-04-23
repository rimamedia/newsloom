"""Tools for database operations through Claude API."""

TOOLS = [
    # Stream execution tools
    {
        "name": "execute_news_stream",
        "description": "Process news items using the specified agent",
        "input_schema": {
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
    },
    {
        "name": "execute_web_scraper",
        "description": "Scrape content for news articles with empty text",
        "input_schema": {
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
    },
    {
        "name": "execute_doc_publisher",
        "description": "Publish docs from database to Telegram channel",
        "input_schema": {
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
    },
    {
        "name": "execute_google_doc_creator",
        "description": "Create Google Docs for documents in the database",
        "input_schema": {
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
    },
    {
        "name": "execute_telegram_bulk_parser",
        "description": "Parse Telegram channels for content",
        "input_schema": {
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
    },
    {
        "name": "execute_link_parser",
        "description": "Enrich links with content using web scraping",
        "input_schema": {
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
    },
    {
        "name": "execute_sitemap_parser",
        "description": "Extract links from a sitemap URL",
        "input_schema": {
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
    },
    {
        "name": "execute_rss_parser",
        "description": "Extract links from an RSS feed URL",
        "input_schema": {
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
    },
    {
        "name": "execute_playwright_extractor",
        "description": "Extract links from a webpage using Playwright",
        "input_schema": {
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
    },
    {
        "name": "execute_search_engine",
        "description": "Search for content using various search engines",
        "input_schema": {
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
                    "description": "For DuckDuckGo: Time range (d=day, w=week, m=month) (default: d)",  # noqa E501
                },
            },
            "required": ["engine", "keywords"],
        },
    },
    # Database operation tools
    {
        "name": "list_media",
        "description": "Get a paginated list of media entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of entries to return (default 50)",
                    "minimum": 1,
                    "maximum": 1000,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of entries to skip (default 0)",
                    "minimum": 0,
                },
            },
        },
    },
    {
        "name": "add_media",
        "description": "Add a new media entry to the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the media"},
                "source_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional list of source IDs to associate with the media",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_media",
        "description": "Update an existing media entry in the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the media to update"},
                "name": {"type": "string", "description": "New name for the media"},
                "source_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of source IDs to associate with the media",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_media",
        "description": "Delete a media entry from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the media to delete"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "list_sources",
        "description": "Get a paginated list of source entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of entries to return (default 50)",
                    "minimum": 1,
                    "maximum": 1000,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of entries to skip (default 0)",
                    "minimum": 0,
                },
            },
        },
    },
    {
        "name": "add_source",
        "description": "Add a new source entry to the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the source"},
                "link": {
                    "type": "string",
                    "description": "Main website URL of the source",
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "web",
                        "telegram",
                        "search",
                        "rss",
                        "twitter",
                        "facebook",
                        "linkedin",
                    ],
                    "description": "Type of the source",
                },
            },
            "required": ["name", "link", "type"],
        },
    },
    {
        "name": "update_source",
        "description": "Update an existing source entry in the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the source to update"},
                "name": {"type": "string", "description": "New name for the source"},
                "link": {
                    "type": "string",
                    "description": "New main website URL of the source",
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "web",
                        "telegram",
                        "search",
                        "rss",
                        "twitter",
                        "facebook",
                        "linkedin",
                    ],
                    "description": "New type for the source",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_source",
        "description": "Delete a source entry from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the source to delete"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "list_streams",
        "description": "Get a paginated list of stream entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "failed", "processing"],
                    "description": "Optional status to filter streams by",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of entries to return (default 50)",
                    "minimum": 1,
                    "maximum": 1000,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of entries to skip (default 0)",
                    "minimum": 0,
                },
            },
        },
    },
    {
        "name": "add_stream",
        "description": "Add a new stream entry to the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the stream"},
                "stream_type": {
                    "type": "string",
                    "enum": [
                        "sitemap_news",
                        "sitemap_blog",
                        "playwright_link_extractor",
                        "rss_feed",
                        "web_article",
                        "telegram_channel",
                        "telegram_publish",
                        "article_searcher",
                        "bing_search",
                        "google_search",
                        "telegram_bulk_parser",
                        "news_stream",
                        "doc_publisher",
                        # Legacy tools removed from available list
                        # "articlean",
                    ],
                    "description": "Type of the stream",
                },
                "source_id": {
                    "type": "integer",
                    "description": "Optional ID of the source to associate with the stream",
                },
                "media_id": {
                    "type": "integer",
                    "description": "Optional ID of the media to associate with the stream",
                },
                "frequency": {
                    "type": "string",
                    "enum": [
                        "5min",
                        "15min",
                        "30min",
                        "1hour",
                        "6hours",
                        "12hours",
                        "daily",
                    ],
                    "description": "How often the stream should run",
                },
                "configuration": {
                    "type": "object",
                    "description": "Stream-specific configuration parameters",
                },
            },
            "required": ["name", "stream_type", "frequency", "configuration"],
        },
    },
    {
        "name": "update_stream",
        "description": "Update an existing stream entry in the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the stream to update"},
                "name": {"type": "string", "description": "New name for the stream"},
                "stream_type": {
                    "type": "string",
                    "enum": [
                        "sitemap_news",
                        "sitemap_blog",
                        "playwright_link_extractor",
                        "rss_feed",
                        "web_article",
                        "telegram_channel",
                        "telegram_publish",
                        "article_searcher",
                        "bing_search",
                        "google_search",
                        "telegram_bulk_parser",
                        "news_stream",
                        "doc_publisher",
                        # Legacy tools removed from available list
                        # "articlean",
                    ],
                    "description": "New type for the stream",
                },
                "source_id": {
                    "type": "integer",
                    "description": "New source ID to associate with the stream",
                },
                "media_id": {
                    "type": "integer",
                    "description": "New media ID to associate with the stream",
                },
                "frequency": {
                    "type": "string",
                    "enum": [
                        "5min",
                        "15min",
                        "30min",
                        "1hour",
                        "6hours",
                        "12hours",
                        "daily",
                    ],
                    "description": "New frequency for the stream",
                },
                "configuration": {
                    "type": "object",
                    "description": "New stream-specific configuration parameters",
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "failed", "processing"],
                    "description": "New status for the stream",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_stream",
        "description": "Delete a stream entry from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the stream to delete"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "list_agents",
        "description": "Get a paginated list of agent entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "is_active": {
                    "type": "boolean",
                    "description": "Optional flag to filter agents by active status",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of entries to return (default 50)",
                    "minimum": 1,
                    "maximum": 1000,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of entries to skip (default 0)",
                    "minimum": 0,
                },
            },
        },
    },
    {
        "name": "add_agent",
        "description": "Add a new agent entry to the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the agent"},
                "description": {
                    "type": "string",
                    "description": "Description of what this agent does",
                },
                "provider": {
                    "type": "string",
                    "enum": ["openai", "anthropic", "google", "bedrock"],
                    "description": "The LLM provider to use",
                },
                "system_prompt": {
                    "type": "string",
                    "description": "The system prompt that defines the agent's behavior",
                },
                "user_prompt_template": {
                    "type": "string",
                    "description": "Template for the user prompt. Must contain {news} placeholder",
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether this agent is active and can be used by streams",
                },
            },
            "required": ["name", "provider", "system_prompt", "user_prompt_template"],
        },
    },
    {
        "name": "update_agent",
        "description": "Update an existing agent entry in the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the agent to update"},
                "name": {"type": "string", "description": "New name for the agent"},
                "description": {
                    "type": "string",
                    "description": "New description of what this agent does",
                },
                "provider": {
                    "type": "string",
                    "enum": ["openai", "anthropic", "google", "bedrock"],
                    "description": "New LLM provider to use",
                },
                "system_prompt": {
                    "type": "string",
                    "description": "New system prompt that defines the agent's behavior",
                },
                "user_prompt_template": {
                    "type": "string",
                    "description": "New template for the user prompt. Must contain {news} placeholder",  # noqa E501
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether this agent is active and can be used by streams",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_agent",
        "description": "Delete an agent entry from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the agent to delete"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "get_stream_logs",
        "description": "Get stream execution logs filtered by stream ID and/or status",
        "input_schema": {
            "type": "object",
            "properties": {
                "stream_id": {
                    "type": "integer",
                    "description": "Optional ID of the stream to get logs for",
                },
                "status": {
                    "type": "string",
                    "enum": ["success", "failed", "running"],
                    "description": "Optional status to filter logs by",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of logs to return (default 100)",
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
        },
    },
    {
        "name": "get_link_classes",
        "description": "Get CSS classes from links on a webpage to help configure link selectors",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to analyze",
                },
                "max_links": {
                    "type": "integer",
                    "description": "Maximum number of links to analyze (default 100)",
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
            "required": ["url"],
        },
    },
]
