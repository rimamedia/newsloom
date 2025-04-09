"""
MCP media tool implementations for Newsloom.

This module provides MCP tool implementations for media-related operations.
"""

import json
import logging

# Import Django models
from django.core.exceptions import ValidationError
from mediamanager.models import Media
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


def register_media_tools(server):
    """
    Register media-related tools with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock media tools")
        return

    @server.tool(
        name="list_media",
        description="Get a paginated list of media entries from the database",
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
    async def list_media(request):
        """
        Get a paginated list of media entries from the database.

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
            queryset = Media.objects.all()

            # Get total count
            total = queryset.count()

            # Get paginated results
            items = [
                {
                    "id": media.id,
                    "name": media.name,
                    "created_at": media.created_at.isoformat(),
                    "updated_at": media.updated_at.isoformat(),
                    "sources": list(media.sources.values_list("id", flat=True)),
                }
                for media in queryset[offset : offset + limit]
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
            logger.error(f"Error listing media: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error listing media: {str(e)}")

    @server.tool(
        name="add_media",
        description="Add a new media entry to the database",
        input_schema={
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
    )
    async def add_media(request):
        """
        Add a new media entry to the database.

        Args:
            request: The MCP request object containing:
                name: Name of the media
                source_ids: Optional list of source IDs to associate with the media

        Returns:
            Dict containing the created media entry
        """
        try:
            args = request.params.arguments
            name = args.get("name")
            source_ids = args.get("source_ids", [])

            # Create media
            media = Media(name=name)
            media.save()

            # Add sources if provided
            if source_ids:
                sources = Source.objects.filter(id__in=source_ids)
                media.sources.add(*sources)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": media.id,
                                "name": media.name,
                                "created_at": media.created_at.isoformat(),
                                "updated_at": media.updated_at.isoformat(),
                                "sources": list(
                                    media.sources.values_list("id", flat=True)
                                ),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except ValidationError as e:
            logger.error(f"Validation error adding media: {str(e)}")
            raise McpError(ErrorCode.InvalidParams, f"Validation error: {str(e)}")
        except Source.DoesNotExist:
            logger.error("One or more sources not found")
            raise McpError(ErrorCode.InvalidParams, "One or more sources not found")
        except Exception as e:
            logger.error(f"Error adding media: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error adding media: {str(e)}")

    @server.tool(
        name="update_media",
        description="Update an existing media entry in the database",
        input_schema={
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
    )
    async def update_media(request):
        """
        Update an existing media entry in the database.

        Args:
            request: The MCP request object containing:
                id: ID of the media to update
                name: Optional new name for the media
                source_ids: Optional list of source IDs to associate with the media

        Returns:
            Dict containing the updated media entry
        """
        try:
            args = request.params.arguments
            media_id = args.get("id")
            name = args.get("name")
            source_ids = args.get("source_ids")

            # Get media
            try:
                media = Media.objects.get(id=media_id)
            except Media.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams, f"Media with id {media_id} does not exist"
                )

            # Update name if provided
            if name is not None:
                media.name = name
                media.save()

            # Update sources if provided
            if source_ids is not None:
                # Clear existing sources
                media.sources.clear()

                # Add new sources
                if source_ids:
                    sources = Source.objects.filter(id__in=source_ids)
                    media.sources.add(*sources)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": media.id,
                                "name": media.name,
                                "created_at": media.created_at.isoformat(),
                                "updated_at": media.updated_at.isoformat(),
                                "sources": list(
                                    media.sources.values_list("id", flat=True)
                                ),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except ValidationError as e:
            logger.error(f"Validation error updating media: {str(e)}")
            raise McpError(ErrorCode.InvalidParams, f"Validation error: {str(e)}")
        except Source.DoesNotExist:
            logger.error("One or more sources not found")
            raise McpError(ErrorCode.InvalidParams, "One or more sources not found")
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error updating media: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error updating media: {str(e)}")

    @server.tool(
        name="delete_media",
        description="Delete a media entry from the database",
        input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the media to delete"},
            },
            "required": ["id"],
        },
    )
    async def delete_media(request):
        """
        Delete a media entry from the database.

        Args:
            request: The MCP request object containing:
                id: ID of the media to delete

        Returns:
            Dict containing success message
        """
        try:
            args = request.params.arguments
            media_id = args.get("id")

            # Get media
            try:
                media = Media.objects.get(id=media_id)
            except Media.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams, f"Media with id {media_id} does not exist"
                )

            # Delete media
            media.delete()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": True,
                                "message": f"Media with id {media_id} deleted successfully",
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
            logger.error(f"Error deleting media: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error deleting media: {str(e)}")
