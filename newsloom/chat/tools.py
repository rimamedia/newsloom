"""Tools for database operations through Claude API."""

TOOLS = [
    {
        "name": "list_media",
        "description": "Get a list of all media entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {},
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
        "description": "Get a list of all source entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {},
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
        "description": "Get a list of all stream entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "failed", "processing"],
                    "description": "Optional status to filter streams by",
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
                        "telegram_test",
                        "article_searcher",
                        "bing_search",
                        "google_search",
                        "telegram_bulk_parser",
                        "news_stream",
                        "doc_publisher",
                        "articlean",
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
        "description": "Get a list of all agent entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "is_active": {
                    "type": "boolean",
                    "description": "Optional flag to filter agents by active status",
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
        "name": "list_docs",
        "description": "Get a list of all doc entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "media_id": {
                    "type": "integer",
                    "description": "Optional ID of media to filter docs by",
                },
                "status": {
                    "type": "string",
                    "enum": ["new", "edit", "publish"],
                    "description": "Optional status to filter docs by",
                },
            },
        },
    },
    {
        "name": "add_doc",
        "description": "Add a new doc entry to the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "media_id": {
                    "type": "integer",
                    "description": "ID of the media this doc belongs to",
                },
                "link": {
                    "type": "string",
                    "description": "Unique URL for the doc",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the doc",
                },
                "text": {
                    "type": "string",
                    "description": "Content text of the doc",
                },
                "status": {
                    "type": "string",
                    "enum": ["new", "edit", "publish"],
                    "description": "Status of the doc",
                },
                "published_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Optional publication date/time",
                },
            },
            "required": ["media_id", "link"],
        },
    },
    {
        "name": "update_doc",
        "description": "Update an existing doc entry in the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "ID of the doc to update",
                },
                "media_id": {
                    "type": "integer",
                    "description": "New media ID for the doc",
                },
                "link": {
                    "type": "string",
                    "description": "New URL for the doc",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the doc",
                },
                "text": {
                    "type": "string",
                    "description": "New content text for the doc",
                },
                "status": {
                    "type": "string",
                    "enum": ["new", "edit", "publish"],
                    "description": "New status for the doc",
                },
                "published_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "New publication date/time",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_doc",
        "description": "Delete a doc entry from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "ID of the doc to delete",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "list_examples",
        "description": "Get a list of all example entries from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "media_id": {
                    "type": "integer",
                    "description": "Optional ID of media to filter examples by",
                },
            },
        },
    },
    {
        "name": "add_example",
        "description": "Add a new example entry to the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "media_id": {
                    "type": "integer",
                    "description": "ID of the media this example belongs to",
                },
                "text": {
                    "type": "string",
                    "description": "Content text of the example",
                },
            },
            "required": ["media_id", "text"],
        },
    },
    {
        "name": "update_example",
        "description": "Update an existing example entry in the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "ID of the example to update",
                },
                "media_id": {
                    "type": "integer",
                    "description": "New media ID for the example",
                },
                "text": {
                    "type": "string",
                    "description": "New content text for the example",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_example",
        "description": "Delete an example entry from the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "ID of the example to delete",
                },
            },
            "required": ["id"],
        },
    },
]
