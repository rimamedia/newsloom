"""
MCP client implementation for Newsloom.

This module provides a client for interacting with the Newsloom MCP server,
allowing for standardized tool operations across chat and agents.
"""

import logging
import subprocess
from typing import Any, Dict, Optional

# Import Django-specific utilities for async operations
from asgiref.sync import sync_to_async

# Import existing tool functions for backward compatibility
from chat.tools import tool_functions

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for interacting with the Newsloom MCP server.

    This client provides methods for calling tools and accessing resources
    exposed by the MCP server. During the migration period, it can fall back
    to direct tool function calls for backward compatibility.
    """

    def __init__(
        self,
        server_process: Optional[subprocess.Popen] = None,
        use_fallback: bool = True,
    ):
        """
        Initialize the MCP client.

        Args:
            server_process: Optional subprocess running the MCP server
            use_fallback: Whether to fall back to direct tool function calls if MCP fails
        """
        self.server_process = server_process
        self.use_fallback = use_fallback
        self._connected = False

    async def connect(self):
        """
        Connect to the MCP server.

        In a real implementation, this would establish a connection to the MCP server.
        For now, we'll just set a flag to indicate that we're connected.
        """
        # In a real implementation, this would establish a connection
        self._connected = True
        logger.info("Connected to MCP server")

    async def disconnect(self):
        """
        Disconnect from the MCP server.

        In a real implementation, this would close the connection to the MCP server.
        """
        # In a real implementation, this would close the connection
        self._connected = False
        logger.info("Disconnected from MCP server")

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments to pass to the tool

        Returns:
            The result of the tool call

        Raises:
            ValueError: If the tool is not found
            Exception: If the tool execution fails
        """
        try:
            # In a real implementation, this would communicate with the MCP server
            # For now, we'll directly import and call the tool functions
            if tool_name not in tool_functions:
                raise ValueError(f"Unknown tool: {tool_name}")

            tool_func = tool_functions[tool_name]

            # Convert synchronous function to asynchronous
            async_tool_func = sync_to_async(tool_func)
            result = await async_tool_func(**kwargs)

            logger.info(f"Tool {tool_name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")

            # If fallback is enabled and this is not a "tool not found" error,
            # try calling the tool function directly
            if self.use_fallback and not isinstance(e, ValueError):
                logger.info(
                    f"Falling back to direct tool function call for {tool_name}"
                )
                try:
                    tool_func = tool_functions[tool_name]
                    async_tool_func = sync_to_async(tool_func)
                    result = await async_tool_func(**kwargs)
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {str(fallback_error)}")
                    raise fallback_error

            raise

    async def get_resource(self, resource_uri: str) -> Dict:
        """
        Get a resource from the MCP server.

        Args:
            resource_uri: URI of the resource to retrieve

        Returns:
            The resource data

        Raises:
            ValueError: If the resource is not found
            Exception: If the resource retrieval fails
        """
        try:
            # In a real implementation, this would communicate with the MCP server
            # For now, we'll parse the URI and retrieve the resource directly

            # Parse the URI to extract the resource type and ID
            # Example URI: newsloom://media/123
            parts = resource_uri.split("://")
            if len(parts) != 2 or parts[0] != "newsloom":
                raise ValueError(f"Invalid resource URI: {resource_uri}")

            path_parts = parts[1].split("/")
            if len(path_parts) < 2:
                raise ValueError(f"Invalid resource path: {parts[1]}")

            resource_type = path_parts[0]
            resource_id = path_parts[1]

            # Handle different resource types
            if resource_type == "media":
                from mediamanager.models import Media

                media = await sync_to_async(Media.objects.get)(id=resource_id)
                return {
                    "id": media.id,
                    "name": media.name,
                    "created_at": media.created_at.isoformat(),
                    "updated_at": media.updated_at.isoformat(),
                    "sources": list(
                        await sync_to_async(media.sources.values_list)("id", flat=True)
                    ),
                }
            elif resource_type == "source":
                from sources.models import Source

                source = await sync_to_async(Source.objects.get)(id=resource_id)
                return {
                    "id": source.id,
                    "name": source.name,
                    "link": source.link,
                    "type": source.type,
                    "created_at": source.created_at.isoformat(),
                    "updated_at": source.updated_at.isoformat(),
                }
            elif resource_type == "stream":
                from streams.models import Stream

                stream = await sync_to_async(Stream.objects.get)(id=resource_id)
                return {
                    "id": stream.id,
                    "name": stream.name,
                    "stream_type": stream.stream_type,
                    "frequency": stream.frequency,
                    "status": stream.status,
                    "configuration": stream.configuration,
                    "created_at": stream.created_at.isoformat(),
                    "updated_at": stream.updated_at.isoformat(),
                }
            elif resource_type == "agent":
                from agents.models import Agent

                agent = await sync_to_async(Agent.objects.get)(id=resource_id)
                return {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "provider": agent.provider,
                    "is_active": agent.is_active,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": agent.updated_at.isoformat(),
                }
            else:
                raise ValueError(f"Unknown resource type: {resource_type}")

        except Exception as e:
            logger.error(f"Error retrieving resource {resource_uri}: {str(e)}")
            raise
