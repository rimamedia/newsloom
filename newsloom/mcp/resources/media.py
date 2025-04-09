"""
MCP media resource implementations for Newsloom.

This module provides MCP resource implementations for media-related data.
"""

import json
import logging

# Import Django models
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
        NotFound = "NotFound"

    class McpError(Exception):
        def __init__(self, code, message):
            self.code = code
            self.message = message
            super().__init__(f"{code}: {message}")

    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


def register_media_resources(server):
    """
    Register media-related resources with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock media resources")
        return

    # Register static resources
    @server.request_handler("list_resources")
    async def list_resources(request):
        """List available static resources."""
        return {
            "resources": [
                {
                    "uri": "newsloom://media/recent",
                    "name": "Recent media entries",
                    "mimeType": "application/json",
                    "description": "List of the 10 most recently created media entries",
                }
            ]
        }

    # Register resource templates
    @server.request_handler("list_resource_templates")
    async def list_resource_templates(request):
        """List available resource templates."""
        return {
            "resourceTemplates": [
                {
                    "uriTemplate": "newsloom://media/{id}",
                    "name": "Media details",
                    "mimeType": "application/json",
                    "description": "Details of a specific media entry",
                }
            ]
        }

    # Register resource handler
    @server.request_handler("read_resource")
    async def read_resource(request):
        """
        Handle resource read requests.

        Args:
            request: The MCP request object containing the resource URI

        Returns:
            Dict containing the resource content
        """
        uri = request.params.uri

        try:
            # Handle static resources
            if uri == "newsloom://media/recent":
                return await _get_recent_media()

            # Handle resource templates
            if uri.startswith("newsloom://media/"):
                # Extract media ID from URI
                parts = uri.split("/")
                if len(parts) != 3:
                    raise McpError(
                        ErrorCode.InvalidRequest, f"Invalid media resource URI: {uri}"
                    )

                media_id = parts[2]
                if media_id == "recent":
                    return await _get_recent_media()

                try:
                    media_id = int(media_id)
                except ValueError:
                    raise McpError(
                        ErrorCode.InvalidRequest, f"Invalid media ID: {media_id}"
                    )

                return await _get_media_by_id(media_id)

            # Unknown resource
            raise McpError(ErrorCode.InvalidRequest, f"Unknown resource URI: {uri}")

        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error reading resource: {str(e)}")


async def _get_recent_media():
    """
    Get the 10 most recently created media entries.

    Returns:
        Dict containing the resource content
    """
    try:
        # Get recent media
        recent_media = Media.objects.order_by("-created_at")[:10]

        # Format response
        items = [
            {
                "id": media.id,
                "name": media.name,
                "created_at": media.created_at.isoformat(),
                "updated_at": media.updated_at.isoformat(),
                "sources": list(media.sources.values_list("id", flat=True)),
            }
            for media in recent_media
        ]

        return {
            "contents": [
                {
                    "uri": "newsloom://media/recent",
                    "mimeType": "application/json",
                    "text": json.dumps(items, indent=2),
                }
            ]
        }

    except Exception as e:
        logger.error(f"Error getting recent media: {str(e)}")
        raise McpError(ErrorCode.InternalError, f"Error getting recent media: {str(e)}")


async def _get_media_by_id(media_id):
    """
    Get a specific media entry by ID.

    Args:
        media_id: ID of the media to retrieve

    Returns:
        Dict containing the resource content

    Raises:
        McpError: If the media is not found
    """
    try:
        # Get media
        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            raise McpError(ErrorCode.NotFound, f"Media with id {media_id} not found")

        # Format response
        media_data = {
            "id": media.id,
            "name": media.name,
            "created_at": media.created_at.isoformat(),
            "updated_at": media.updated_at.isoformat(),
            "sources": list(media.sources.values_list("id", flat=True)),
        }

        return {
            "contents": [
                {
                    "uri": f"newsloom://media/{media_id}",
                    "mimeType": "application/json",
                    "text": json.dumps(media_data, indent=2),
                }
            ]
        }

    except McpError:
        # Re-raise MCP errors
        raise
    except Exception as e:
        logger.error(f"Error getting media {media_id}: {str(e)}")
        raise McpError(ErrorCode.InternalError, f"Error getting media: {str(e)}")
