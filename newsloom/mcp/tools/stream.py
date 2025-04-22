"""
MCP stream tool implementations for Newsloom.

This module provides MCP tool implementations for stream-related operations.
"""

import json
import logging

# Import Django models
from django.core.exceptions import ValidationError
from streams.models import Stream
from sources.models import Source
from mediamanager.models import Media

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

    @server.tool(
        name="add_stream",
        description="Add a new stream entry to the database",
        input_schema={
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
    )
    async def add_stream(request):
        """
        Add a new stream entry to the database.

        Args:
            request: The MCP request object containing:
                name: Name of the stream
                stream_type: Type of the stream
                source_id: Optional ID of the source to associate with the stream
                media_id: Optional ID of the media to associate with the stream
                frequency: How often the stream should run
                configuration: Stream-specific configuration parameters

        Returns:
            Dict containing the created stream entry
        """
        try:
            args = request.params.arguments
            name = args.get("name")
            stream_type = args.get("stream_type")
            source_id = args.get("source_id")
            media_id = args.get("media_id")
            frequency = args.get("frequency")
            configuration = args.get("configuration", {})

            # Validate source_id if provided
            if source_id:
                try:
                    Source.objects.get(id=source_id)
                except Source.DoesNotExist:
                    raise McpError(
                        ErrorCode.InvalidParams,
                        f"Source with id {source_id} does not exist",
                    )

            # Validate media_id if provided
            if media_id:
                try:
                    Media.objects.get(id=media_id)
                except Media.DoesNotExist:
                    raise McpError(
                        ErrorCode.InvalidParams,
                        f"Media with id {media_id} does not exist",
                    )

            # Create stream
            stream = Stream(
                name=name,
                stream_type=stream_type,
                source_id=source_id,
                media_id=media_id,
                frequency=frequency,
                configuration=configuration,
                status="active",  # Default status
            )
            stream.save()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": stream.id,
                                "name": stream.name,
                                "stream_type": stream.stream_type,
                                "frequency": stream.frequency,
                                "status": stream.status,
                                "source_id": stream.source_id,
                                "media_id": stream.media_id,
                                "configuration": stream.configuration,
                                "created_at": stream.created_at.isoformat(),
                                "updated_at": stream.updated_at.isoformat(),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except ValidationError as e:
            logger.error(f"Validation error adding stream: {str(e)}")
            raise McpError(ErrorCode.InvalidParams, f"Validation error: {str(e)}")
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error adding stream: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error adding stream: {str(e)}")

    @server.tool(
        name="update_stream",
        description="Update an existing stream entry in the database",
        input_schema={
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
    )
    async def update_stream(request):
        """
        Update an existing stream entry in the database.

        Args:
            request: The MCP request object containing:
                id: ID of the stream to update
                name: Optional new name for the stream
                stream_type: Optional new type for the stream
                source_id: Optional new source ID to associate with the stream
                media_id: Optional new media ID to associate with the stream
                frequency: Optional new frequency for the stream
                configuration: Optional new stream-specific configuration parameters
                status: Optional new status for the stream

        Returns:
            Dict containing the updated stream entry
        """
        try:
            args = request.params.arguments
            stream_id = args.get("id")
            name = args.get("name")
            stream_type = args.get("stream_type")
            source_id = args.get("source_id")
            media_id = args.get("media_id")
            frequency = args.get("frequency")
            configuration = args.get("configuration")
            status = args.get("status")

            # Get stream
            try:
                stream = Stream.objects.get(id=stream_id)
            except Stream.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Stream with id {stream_id} does not exist",
                )

            # Validate source_id if provided
            if source_id is not None:
                if source_id == 0:
                    # Allow clearing the source_id by setting it to 0
                    source_id = None
                elif source_id > 0:
                    try:
                        Source.objects.get(id=source_id)
                    except Source.DoesNotExist:
                        raise McpError(
                            ErrorCode.InvalidParams,
                            f"Source with id {source_id} does not exist",
                        )

            # Validate media_id if provided
            if media_id is not None:
                if media_id == 0:
                    # Allow clearing the media_id by setting it to 0
                    media_id = None
                elif media_id > 0:
                    try:
                        Media.objects.get(id=media_id)
                    except Media.DoesNotExist:
                        raise McpError(
                            ErrorCode.InvalidParams,
                            f"Media with id {media_id} does not exist",
                        )

            # Update fields if provided
            if name is not None:
                stream.name = name
            if stream_type is not None:
                stream.stream_type = stream_type
            if source_id is not None:
                stream.source_id = source_id
            if media_id is not None:
                stream.media_id = media_id
            if frequency is not None:
                stream.frequency = frequency
            if configuration is not None:
                stream.configuration = configuration
            if status is not None:
                stream.status = status

            # Save changes
            stream.save()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": stream.id,
                                "name": stream.name,
                                "stream_type": stream.stream_type,
                                "frequency": stream.frequency,
                                "status": stream.status,
                                "source_id": stream.source_id,
                                "media_id": stream.media_id,
                                "configuration": stream.configuration,
                                "created_at": stream.created_at.isoformat(),
                                "updated_at": stream.updated_at.isoformat(),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except ValidationError as e:
            logger.error(f"Validation error updating stream: {str(e)}")
            raise McpError(ErrorCode.InvalidParams, f"Validation error: {str(e)}")
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error updating stream: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error updating stream: {str(e)}")

    @server.tool(
        name="delete_stream",
        description="Delete a stream entry from the database",
        input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the stream to delete"},
            },
            "required": ["id"],
        },
    )
    async def delete_stream(request):
        """
        Delete a stream entry from the database.

        Args:
            request: The MCP request object containing:
                id: ID of the stream to delete

        Returns:
            Dict containing success message
        """
        try:
            args = request.params.arguments
            stream_id = args.get("id")

            # Get stream
            try:
                stream = Stream.objects.get(id=stream_id)
            except Stream.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Stream with id {stream_id} does not exist",
                )

            # Delete stream
            stream.delete()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": True,
                                "message": f"Stream with id {stream_id} deleted successfully",
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
            logger.error(f"Error deleting stream: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error deleting stream: {str(e)}")
