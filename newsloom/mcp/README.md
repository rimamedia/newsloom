# Newsloom MCP (Model Context Protocol) Implementation

This module provides a standardized way to define and expose tools and resources to AI models, allowing for consistent tool operations across chat and agents in the Newsloom platform.

## Overview

The Model Context Protocol (MCP) is a standardized interface for AI models to interact with external tools and resources. This implementation provides a server that exposes Newsloom's functionality as MCP tools and resources, and a client that can be used to interact with the server.

## Architecture

The MCP implementation consists of the following components:

### Server

The `NewsloomMCPServer` class in `server.py` is the main server implementation. It exposes tools and resources for interacting with the Newsloom database and functionality.

### Client

The `MCPClient` class in `client.py` provides a client for interacting with the MCP server. It can be used to call tools and access resources exposed by the server.

### Tools

Tools are implemented in the `tools` package. Each tool is a function that performs a specific operation, such as creating, reading, updating, or deleting a database record. Tools are registered with the server and can be called by the client.

### Resources

Resources are implemented in the `resources` package. Each resource represents a data source, such as a database record or a collection of records. Resources are registered with the server and can be accessed by the client.

## Usage

### Running the Server

To run the MCP server, use the `run_mcp_server` management command:

```bash
python manage.py run_mcp_server
```

This will start the MCP server, which will listen for requests from clients.

### Using the Client

To use the MCP client in your code, import the `MCPClient` class and create an instance:

```python
from mcp.client import MCPClient

client = MCPClient()
```

Then, you can use the client to call tools and access resources:

```python
# Call a tool
result = await client.call_tool("list_media", limit=10, offset=0)

# Access a resource
media = await client.get_resource("newsloom://media/123")
```

### Integration with Chat

The MCP client is integrated with the chat system in `chat/message_processor.py`. When a tool call is detected in an AI response, the `_process_tool_calls` method uses the MCP client to execute the tool and add the result to the chat history.

## Tool Categories

The MCP implementation includes tools for the following categories:

### Media Tools

Tools for managing media entries in the database:

- `list_media`: Get a paginated list of media entries
- `add_media`: Add a new media entry
- `update_media`: Update an existing media entry
- `delete_media`: Delete a media entry

### Source Tools

Tools for managing source entries in the database:

- `list_sources`: Get a paginated list of source entries
- `add_source`: Add a new source entry
- `update_source`: Update an existing source entry
- `delete_source`: Delete a source entry

### Stream Tools

Tools for managing stream entries in the database:

- `list_streams`: Get a paginated list of stream entries
- `add_stream`: Add a new stream entry
- `update_stream`: Update an existing stream entry
- `delete_stream`: Delete a stream entry
- `get_stream_logs`: Get stream execution logs

### Agent Tools

Tools for managing agent entries in the database:

- `list_agents`: Get a paginated list of agent entries
- `add_agent`: Add a new agent entry
- `update_agent`: Update an existing agent entry
- `delete_agent`: Delete a agent entry
- `run_agent`: Run an agent with the provided input text

## Resource Categories

The MCP implementation includes resources for the following categories:

### Media Resources

Resources for accessing media data:

- `newsloom://media/recent`: List of the 10 most recently created media entries
- `newsloom://media/{id}`: Details of a specific media entry

### Source Resources

Resources for accessing source data:

- `newsloom://source/recent`: List of the 10 most recently created source entries
- `newsloom://source/{id}`: Details of a specific source entry

### Stream Resources

Resources for accessing stream data:

- `newsloom://stream/recent`: List of the 10 most recently created stream entries
- `newsloom://stream/active`: List of all active streams
- `newsloom://stream/failed`: List of all failed streams
- `newsloom://stream/{id}`: Details of a specific stream entry
- `newsloom://stream/{id}/logs`: Execution logs for a specific stream

### Agent Resources

Resources for accessing agent data:

- `newsloom://agent/recent`: List of the 10 most recently created agent entries
- `newsloom://agent/active`: List of all active agents
- `newsloom://agent/{id}`: Details of a specific agent entry
- `newsloom://agent/provider/{provider}`: List of agents for a specific provider

## Development

### Adding New Tools

To add a new tool, create a function in the appropriate module in the `tools` package and register it with the server in the module's `register_*_tools` function.

### Adding New Resources

To add a new resource, update the appropriate module in the `resources` package and register it with the server in the module's `register_*_resources` function.

## Dependencies

The MCP implementation depends on the following packages:

- `mcp`: The MCP SDK package (optional, mock implementations are provided if not available)
- Django and its dependencies

## Error Handling

The MCP implementation includes comprehensive error handling to ensure that errors are properly reported to clients. Each tool and resource handler includes try-except blocks to catch and handle exceptions, and the server includes an error handler to log errors.
