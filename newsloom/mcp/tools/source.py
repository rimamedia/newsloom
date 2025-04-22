"""
MCP source tool implementations for Newsloom.

This module provides MCP tool implementations for source-related operations.
"""

import json
import logging

# Import Django models
from django.core.exceptions import ValidationError
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

    @server.tool(
        name="add_source",
        description="Add a new source entry to the database",
        input_schema={
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
    )
    async def add_source(request):
        """
        Add a new source entry to the database.

        Args:
            request: The MCP request object containing:
                name: Name of the source
                link: Main website URL of the source
                type: Type of the source

        Returns:
            Dict containing the created source entry
        """
        try:
            args = request.params.arguments
            name = args.get("name")
            link = args.get("link")
            source_type = args.get("type")

            # Create source
            source = Source(name=name, link=link, type=source_type)
            source.save()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": source.id,
                                "name": source.name,
                                "link": source.link,
                                "type": source.type,
                                "created_at": source.created_at.isoformat(),
                                "updated_at": source.updated_at.isoformat(),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except ValidationError as e:
            logger.error(f"Validation error adding source: {str(e)}")
            raise McpError(ErrorCode.InvalidParams, f"Validation error: {str(e)}")
        except Exception as e:
            logger.error(f"Error adding source: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error adding source: {str(e)}")

    @server.tool(
        name="update_source",
        description="Update an existing source entry in the database",
        input_schema={
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
    )
    async def update_source(request):
        """
        Update an existing source entry in the database.

        Args:
            request: The MCP request object containing:
                id: ID of the source to update
                name: Optional new name for the source
                link: Optional new main website URL of the source
                type: Optional new type for the source

        Returns:
            Dict containing the updated source entry
        """
        try:
            args = request.params.arguments
            source_id = args.get("id")
            name = args.get("name")
            link = args.get("link")
            source_type = args.get("type")

            # Get source
            try:
                source = Source.objects.get(id=source_id)
            except Source.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Source with id {source_id} does not exist",
                )

            # Update fields if provided
            if name is not None:
                source.name = name
            if link is not None:
                source.link = link
            if source_type is not None:
                source.type = source_type

            # Save changes
            source.save()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": source.id,
                                "name": source.name,
                                "link": source.link,
                                "type": source.type,
                                "created_at": source.created_at.isoformat(),
                                "updated_at": source.updated_at.isoformat(),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except ValidationError as e:
            logger.error(f"Validation error updating source: {str(e)}")
            raise McpError(ErrorCode.InvalidParams, f"Validation error: {str(e)}")
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error updating source: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error updating source: {str(e)}")

    @server.tool(
        name="delete_source",
        description="Delete a source entry from the database",
        input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the source to delete"},
            },
            "required": ["id"],
        },
    )
    async def delete_source(request):
        """
        Delete a source entry from the database.

        Args:
            request: The MCP request object containing:
                id: ID of the source to delete

        Returns:
            Dict containing success message
        """
        try:
            args = request.params.arguments
            source_id = args.get("id")

            # Get source
            try:
                source = Source.objects.get(id=source_id)
            except Source.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams,
                    f"Source with id {source_id} does not exist",
                )

            # Delete source
            source.delete()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": True,
                                "message": f"Source with id {source_id} deleted successfully",
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
            logger.error(f"Error deleting source: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error deleting source: {str(e)}")
