"""Tools for news stream processing."""

NEWS_PROCESSING_TOOLS = [
    {
        "name": "create_documents",
        "description": "Create a list of documents from the analyzed news content",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The main topic or theme of the documents",
                },
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text content of the document",
                            },
                            "url": {
                                "type": "string",
                                "description": "The source URL for the document",
                            },
                        },
                        "required": ["text", "url"],
                    },
                    "description": "Array of documents to create",
                },
            },
            "required": ["topic", "documents"],
        },
    }
]
