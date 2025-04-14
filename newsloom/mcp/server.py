"""
MCP server implementation for Newsloom.

This module provides the main MCP server implementation that exposes tools and resources
for interacting with the Newsloom database and functionality.
"""

import asyncio
import logging

# Import MCP SDK components
# Note: In a real implementation, you would install the MCP SDK package
# For this example, we'll assume it's available
try:
    from mcp import Server
    from mcp.server.stdio import StdioServerTransport
    from mcp.types import (
        CallToolRequestSchema,
        ErrorCode,
        ListResourcesRequestSchema,
        ListResourceTemplatesRequestSchema,
        ListToolsRequestSchema,
        McpError,
        ReadResourceRequestSchema,
    )

    MCP_AVAILABLE = True
except ImportError:
    # Mock implementations for development without MCP SDK
    class Server:
        def __init__(self, *args, **kwargs):
            pass

        def setRequestHandler(self, *args, **kwargs):
            pass

        async def connect(self, *args, **kwargs):
            pass

        async def close(self):
            pass

    class StdioServerTransport:
        pass

    # Mock schema classes
    CallToolRequestSchema = "CallToolRequestSchema"
    ListResourcesRequestSchema = "ListResourcesRequestSchema"
    ListResourceTemplatesRequestSchema = "ListResourceTemplatesRequestSchema"
    ListToolsRequestSchema = "ListToolsRequestSchema"
    ReadResourceRequestSchema = "ReadResourceRequestSchema"

    # Mock error classes
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


class NewsloomMCPServer:
    """
    MCP server implementation for Newsloom.

    This server exposes tools and resources for interacting with the Newsloom
    database and functionality.
    """

    def __init__(self):
        """Initialize the MCP server with metadata and capabilities."""
        self.server = Server(
            {
                "name": "newsloom-mcp-server",
                "version": "1.0.0",
                "description": "MCP server for Newsloom news processing platform",
            },
            {
                "capabilities": {
                    "tools": {},
                    "resources": {},
                }
            },
        )

        # Set up request handlers
        self._setup_tool_handlers()
        self._setup_resource_handlers()

        # Error handling
        self.server.onerror = self._handle_error

    def _setup_tool_handlers(self):
        """Register tool request handlers."""
        if not MCP_AVAILABLE:
            logger.warning("MCP SDK not available, skipping tool handler setup")
            return

        from .tools import register_all_tools

        register_all_tools(self.server)

    def _setup_resource_handlers(self):
        """Register resource request handlers."""
        if not MCP_AVAILABLE:
            logger.warning("MCP SDK not available, skipping resource handler setup")
            return

        from .resources import register_all_resources

        register_all_resources(self.server)

    def _handle_error(self, error):
        """Handle MCP server errors."""
        logger.error(f"MCP Server Error: {error}")

    async def start(self):
        """Start the MCP server with stdio transport."""
        if not MCP_AVAILABLE:
            logger.error("MCP SDK not available, cannot start server")
            return

        transport = StdioServerTransport()
        await self.server.connect(transport)
        logger.info("MCP server started with stdio transport")

    async def stop(self):
        """Stop the MCP server."""
        if not MCP_AVAILABLE:
            return

        await self.server.close()
        logger.info("MCP server stopped")


async def run_server():
    """Run the MCP server."""
    server = NewsloomMCPServer()
    await server.start()

    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await server.stop()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the server
    asyncio.run(run_server())
