"""
MCP source tool implementations for Newsloom.

This module provides MCP tool implementations for source-related operations.
"""

import json
import logging

# Import Django models
from sources.models import Source

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


def register_source_tools(server):
    """
    Register source-related tools with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock source tools")
        return

    @server.tool(
        name="list_sources",
        description="Get a paginated list of source entries from the database",
        input_schema={
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
    )
    async def list_sources(request):
        """
        Get a paginated list of source entries from the database.

        Args:
            request: The MCP request object containing:
                limit: Maximum number of entries to return (default 50)
                offset: Number of entries to skip (default 0)

        Returns:
            Dict containing items, total count, limit, and offset
        """
        try:
            args = request.params.arguments
            limit = args.get("limit", 50)
            offset = args.get("offset", 0)

            # Build queryset
            queryset = Source.objects.all()

            # Get total count
            total = queryset.count()

            # Get paginated results
            items = [
                {
                    "id": source.id,
                    "name": source.name,
                    "link": source.link,
                    "type": source.type,
                    "created_at": source.created_at.isoformat(),
                    "updated_at": source.updated_at.isoformat(),
                }
                for source in queryset[offset : offset + limit]
            ]

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "items": items,
                                "total": total,
                                "limit": limit,
                                "offset": offset,
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Error listing sources: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error listing sources: {str(e)}")

    # TODO: Implement add_source, update_source, and delete_source tools
    # These would follow a similar pattern to the media tools
