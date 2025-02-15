# fmt: off
from .agent import add_agent, delete_agent, list_agents, update_agent
from .link_classes import get_link_classes
from .media import add_media, delete_media, list_media, update_media
from .source import add_source, delete_source, list_sources, update_source
from .stream import add_stream, delete_stream, get_stream_logs, list_streams, update_stream

tool_functions = {
    "list_media": list_media,
    "add_media": add_media,
    "update_media": update_media,
    "delete_media": delete_media,
    "list_sources": list_sources,
    "add_source": add_source,
    "update_source": update_source,
    "delete_source": delete_source,
    "list_streams": list_streams,
    "add_stream": add_stream,
    "update_stream": update_stream,
    "delete_stream": delete_stream,
    "list_agents": list_agents,
    "add_agent": add_agent,
    "update_agent": update_agent,
    "delete_agent": delete_agent,
    "get_stream_logs": get_stream_logs,
    "get_link_classes": get_link_classes,
}

__all__ = [
    "tool_functions",
    "list_media",
    "add_media",
    "update_media",
    "delete_media",
    "list_sources",
    "add_source",
    "update_source",
    "delete_source",
    "list_streams",
    "add_stream",
    "update_stream",
    "delete_stream",
    "list_agents",
    "add_agent",
    "update_agent",
    "delete_agent",
    "get_stream_logs",
    "link_classes",
    "get_link_classes",
]
