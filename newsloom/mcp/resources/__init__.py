"""
MCP resource implementations for Newsloom.

This module provides resource implementations that can be registered with the MCP server.
"""


def register_all_resources(server):
    """
    Register all resources with the MCP server.

    Args:
        server: The MCP server instance
    """
    from .media import register_media_resources
    from .source import register_source_resources
    from .stream import register_stream_resources
    from .agent import register_agent_resources

    register_media_resources(server)
    register_source_resources(server)
    register_stream_resources(server)
    register_agent_resources(server)
