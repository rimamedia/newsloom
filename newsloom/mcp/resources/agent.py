"""
MCP agent resource implementations for Newsloom.

This module provides MCP resource implementations for agent-related data.
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


def register_agent_resources(server):
    """
    Register agent-related resources with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock agent resources")
        return

    # Register static resources
    @server.request_handler("list_resources")
    async def list_resources(request):
        """List available static resources."""
        return {
            "resources": [
                {
                    "uri": "newsloom://agent/recent",
                    "name": "Recent agent entries",
                    "mimeType": "application/json",
                    "description": "List of the 10 most recently created agent entries",
                },
                {
                    "uri": "newsloom://agent/active",
                    "name": "Active agents",
                    "mimeType": "application/json",
                    "description": "List of all active agents",
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
                    "uriTemplate": "newsloom://agent/{id}",
                    "name": "Agent details",
                    "mimeType": "application/json",
                    "description": "Details of a specific agent entry",
                },
                {
                    "uriTemplate": "newsloom://agent/provider/{provider}",
                    "name": "Agents by provider",
                    "mimeType": "application/json",
                    "description": "List of agents for a specific provider",
                },
            ]
        }

    # TODO: Implement read_resource handler for agent resources
    # This would follow a similar pattern to the media resources
