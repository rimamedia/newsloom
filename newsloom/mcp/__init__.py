"""
Model Context Protocol (MCP) implementation for Newsloom.

This module provides a standardized way to define and expose tools and resources
to AI models, allowing for consistent tool operations across chat and agents.
"""

from .server import NewsloomMCPServer
from .client import MCPClient

__all__ = ["NewsloomMCPServer", "MCPClient"]
