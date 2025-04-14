"""
MCP tool implementations for Newsloom.

This module provides tool implementations that can be registered with the MCP server.
"""


def register_all_tools(server):
    """
    Register all tools with the MCP server.

    Args:
        server: The MCP server instance
    """
    from .media import register_media_tools
    from .source import register_source_tools
    from .stream import register_stream_tools
    from .agent import register_agent_tools

    register_media_tools(server)
    register_source_tools(server)
    register_stream_tools(server)
    register_agent_tools(server)
