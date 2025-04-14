"""
MCP agent tool implementations for Newsloom.

This module provides MCP tool implementations for agent-related operations.
"""

import json
import logging

# Import Django models
from agents.models import Agent

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

    class McpError(Exception):
        def __init__(self, code, message):
            self.code = code
            self.message = message
            super().__init__(f"{code}: {message}")

    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


def register_agent_tools(server):
    """
    Register agent-related tools with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock agent tools")
        return

    @server.tool(
        name="list_agents",
        description="Get a paginated list of agent entries from the database",
        input_schema={
            "type": "object",
            "properties": {
                "is_active": {
                    "type": "boolean",
                    "description": "Optional flag to filter agents by active status",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of entries to return (default 50)",
                    "minimum": 1,
                    "maximum": 1000,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of entries to skip (default 0)",
                    "minimum": 0,
                },
            },
        },
    )
    async def list_agents(request):
        """
        Get a paginated list of agent entries from the database.

        Args:
            request: The MCP request object containing:
                is_active: Optional flag to filter agents by active status
                limit: Maximum number of entries to return (default 50)
                offset: Number of entries to skip (default 0)

        Returns:
            Dict containing items, total count, limit, and offset
        """
        try:
            args = request.params.arguments
            is_active = args.get("is_active")
            limit = args.get("limit", 50)
            offset = args.get("offset", 0)

            # Build queryset
            queryset = Agent.objects.all()

            # Apply is_active filter if provided
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active)

            # Get total count
            total = queryset.count()

            # Get paginated results
            items = [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "provider": agent.provider,
                    "is_active": agent.is_active,
                    "created_at": agent.created_at.isoformat(),
                    "updated_at": agent.updated_at.isoformat(),
                }
                for agent in queryset[offset : offset + limit]
            ]

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "items": items,
                                "total": total,
                                "limit": limit,
                                "offset": offset,
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error listing agents: {str(e)}")

    @server.tool(
        name="run_agent",
        description="Run an agent with the provided input text",
        input_schema={
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "integer",
                    "description": "ID of the agent to run",
                },
                "input_text": {
                    "type": "string",
                    "description": "Input text to process with the agent",
                },
            },
            "required": ["agent_id", "input_text"],
        },
    )
    async def run_agent(request):
        """
        Run an agent with the provided input text.

        Args:
            request: The MCP request object containing:
                agent_id: ID of the agent to run
                input_text: Input text to process with the agent

        Returns:
            Dict containing the agent's response
        """
        try:
            args = request.params.arguments
            agent_id = args.get("agent_id")
            input_text = args.get("input_text")

            # Get agent
            try:
                agent = Agent.objects.get(id=agent_id)
            except Agent.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams, f"Agent with id {agent_id} does not exist"
                )

            # Check if agent is active
            if not agent.is_active:
                raise McpError(
                    ErrorCode.InvalidParams, f"Agent with id {agent_id} is not active"
                )

            # Prepare user prompt
            try:
                user_prompt = agent.user_prompt_template.format(news=input_text)
            except KeyError as e:
                raise McpError(
                    ErrorCode.InternalError, f"Error formatting user prompt: {str(e)}"
                )
            except Exception as e:
                raise McpError(
                    ErrorCode.InternalError, f"Error preparing user prompt: {str(e)}"
                )

            # Run agent
            # In a real implementation, this would call the appropriate LLM provider
            # For now, we'll just return a placeholder response

            # TODO: Implement actual agent execution
            # This would involve calling the appropriate LLM provider based on agent.provider

            response = f"Agent {agent.name} processed the input: {input_text[:50]}..."

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "agent_id": agent.id,
                                "agent_name": agent.name,
                                "provider": agent.provider,
                                "response": response,
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error running agent: {str(e)}")

    # TODO: Implement add_agent, update_agent, and delete_agent tools
    # These would follow a similar pattern to the media tools
