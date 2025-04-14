"""
Tests for the MCP module.

This module contains tests for the MCP server and client implementations.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from .client import MCPClient
from .server import NewsloomMCPServer


class MCPClientTests(TestCase):
    """Tests for the MCP client."""

    def setUp(self):
        """Set up test environment."""
        self.client = MCPClient()

    @patch("mcp.client.sync_to_async")
    async def test_call_tool(self, mock_sync_to_async):
        """Test calling a tool through the MCP client."""
        # Mock the tool function
        mock_tool_func = MagicMock(return_value={"items": [], "total": 0})
        mock_sync_to_async.return_value = AsyncMock(
            return_value=mock_tool_func.return_value
        )

        # Call the tool
        result = await self.client.call_tool("list_media", limit=10, offset=0)

        # Check that the tool function was called with the correct arguments
        self.assertEqual(result, {"items": [], "total": 0})

    @patch("mcp.client.sync_to_async")
    async def test_get_resource(self, mock_sync_to_async):
        """Test getting a resource through the MCP client."""
        # Mock the resource
        mock_media = MagicMock()
        mock_media.id = 123
        mock_media.name = "Test Media"
        mock_media.created_at.isoformat.return_value = "2025-01-01T00:00:00"
        mock_media.updated_at.isoformat.return_value = "2025-01-01T00:00:00"
        mock_media.sources.values_list.return_value = []

        # Mock the get method
        mock_get = MagicMock(return_value=mock_media)
        mock_sync_to_async.return_value = AsyncMock(return_value=mock_get.return_value)

        # Get the resource
        with patch("mcp.client.Media.objects.get", mock_get):
            result = await self.client.get_resource("newsloom://media/123")

        # Check that the resource was retrieved correctly
        self.assertEqual(result["id"], 123)
        self.assertEqual(result["name"], "Test Media")


class MCPServerTests(TestCase):
    """Tests for the MCP server."""

    def setUp(self):
        """Set up test environment."""
        self.server = NewsloomMCPServer()

    @patch("mcp.server.Server")
    def test_init(self, mock_server):
        """Test server initialization."""
        # Check that the server was initialized with the correct parameters
        mock_server.assert_called_once()
        self.assertEqual(self.server.server, mock_server.return_value)

    @patch("mcp.server.StdioServerTransport")
    @patch("mcp.server.Server")
    async def test_start(self, mock_server, mock_transport):
        """Test starting the server."""
        # Mock the connect method
        mock_server.return_value.connect = AsyncMock()

        # Start the server
        await self.server.start()

        # Check that the server was started with the correct transport
        mock_transport.assert_called_once()
        mock_server.return_value.connect.assert_called_once_with(
            mock_transport.return_value
        )

    @patch("mcp.server.Server")
    async def test_stop(self, mock_server):
        """Test stopping the server."""
        # Mock the close method
        mock_server.return_value.close = AsyncMock()

        # Stop the server
        await self.server.stop()

        # Check that the server was closed
        mock_server.return_value.close.assert_called_once()


def run_async_test(coro):
    """Run an async test."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


if __name__ == "__main__":
    unittest.main()
