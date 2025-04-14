"""
MCP stream resource implementations for Newsloom.

This module provides MCP resource implementations for stream-related data.
"""

import logging

# Import Django models

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


def register_stream_resources(server):
    """
    Register stream-related resources with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock stream resources")
        return

    # Register static resources
    @server.request_handler("list_resources")
    async def list_resources(request):
        """List available static resources."""
        return {
            "resources": [
                {
                    "uri": "newsloom://stream/recent",
                    "name": "Recent stream entries",
                    "mimeType": "application/json",
                    "description": "List of the 10 most recently created stream entries",
                },
                {
                    "uri": "newsloom://stream/active",
                    "name": "Active streams",
                    "mimeType": "application/json",
                    "description": "List of all active streams",
                },
                {
                    "uri": "newsloom://stream/failed",
                    "name": "Failed streams",
                    "mimeType": "application/json",
                    "description": "List of all failed streams",
                },
            ]
        }

    # Register resource templates
    @server.request_handler("list_resource_templates")
    async def list_resource_templates(request):
        """List available resource templates."""
        return {
            "resourceTemplates": [
                {
                    "uriTemplate": "newsloom://stream/{id}",
                    "name": "Stream details",
                    "mimeType": "application/json",
                    "description": "Details of a specific stream entry",
                },
                {
                    "uriTemplate": "newsloom://stream/{id}/logs",
                    "name": "Stream logs",
                    "mimeType": "application/json",
                    "description": "Execution logs for a specific stream",
                },
            ]
        }

    # TODO: Implement read_resource handler for stream resources
    # This would follow a similar pattern to the media resources
