"""Tools for database operations through Claude API."""

TOOLS = [
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
                        "telegram_test",
                        "article_searcher",
                        "bing_search",
                        "google_search",
                        "telegram_bulk_parser",
                        "news_stream",
                        "doc_publisher",
                        "articlean",
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
]
