"""
MCP stream tool implementations for Newsloom.

This module provides MCP tool implementations for stream-related operations.
"""

import json
import logging

# Import Django models
from streams.models import Stream

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


def register_stream_tools(server):
    """
    Register stream-related tools with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock stream tools")
        return

    @server.tool(
        name="list_streams",
        description="Get a paginated list of stream entries from the database",
        input_schema={
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
    )
    async def list_streams(request):
        """
        Get a paginated list of stream entries from the database.

        Args:
            request: The MCP request object containing:
                status: Optional status to filter streams by
                limit: Maximum number of entries to return (default 50)
                offset: Number of entries to skip (default 0)

        Returns:
            Dict containing items, total count, limit, and offset
        """
        try:
            args = request.params.arguments
            status = args.get("status")
            limit = args.get("limit", 50)
            offset = args.get("offset", 0)

            # Build queryset
            queryset = Stream.objects.all()

            # Apply status filter if provided
            if status:
                queryset = queryset.filter(status=status)

            # Get total count
            total = queryset.count()

            # Get paginated results
            items = [
                {
                    "id": stream.id,
                    "name": stream.name,
                    "stream_type": stream.stream_type,
                    "frequency": stream.frequency,
                    "status": stream.status,
                    "source_id": stream.source_id,
                    "media_id": stream.media_id,
                    "created_at": stream.created_at.isoformat(),
                    "updated_at": stream.updated_at.isoformat(),
                }
                for stream in queryset[offset : offset + limit]
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
            logger.error(f"Error listing streams: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error listing streams: {str(e)}")

    @server.tool(
        name="get_stream_logs",
        description="Get stream execution logs filtered by stream ID and/or status",
        input_schema={
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
    )
    async def get_stream_logs(request):
        """
        Get stream execution logs filtered by stream ID and/or status.

        Args:
            request: The MCP request object containing:
                stream_id: Optional ID of the stream to get logs for
                status: Optional status to filter logs by
                limit: Optional maximum number of logs to return (default 100)

        Returns:
            Dict containing log entries
        """
        try:
            args = request.params.arguments
            stream_id = args.get("stream_id")
            status = args.get("status")
            limit = args.get("limit", 100)

            # Import here to avoid circular imports
            from streams.models import LuigiTaskLog

            # Build queryset
            queryset = LuigiTaskLog.objects.all()

            # Apply stream_id filter if provided
            if stream_id:
                queryset = queryset.filter(stream_id=stream_id)

            # Apply status filter if provided
            if status:
                queryset = queryset.filter(status=status)

            # Order by most recent first
            queryset = queryset.order_by("-created_at")

            # Get limited results
            logs = [
                {
                    "id": log.id,
                    "stream_id": log.stream_id,
                    "task_id": log.task_id,
                    "status": log.status,
                    "message": log.message,
                    "created_at": log.created_at.isoformat(),
                }
                for log in queryset[:limit]
            ]

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "logs": logs,
                                "count": len(logs),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Error getting stream logs: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error getting stream logs: {str(e)}"
            )

    # TODO: Implement add_stream, update_stream, and delete_stream tools
    # These would follow a similar pattern to the media tools
