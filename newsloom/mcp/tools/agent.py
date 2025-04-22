"""
MCP agent tool implementations for Newsloom.

This module provides MCP tool implementations for agent-related operations.
"""

import json
import logging

# Import Django models
from django.core.exceptions import ValidationError
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

            # Validate that the user prompt template can be formatted
            try:
                agent.user_prompt_template.format(news=input_text)
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

    @server.tool(
        name="add_agent",
        description="Add a new agent entry to the database",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the agent"},
                "description": {
                    "type": "string",
                    "description": "Description of what this agent does",
                },
                "provider": {
                    "type": "string",
                    "enum": ["openai", "anthropic", "google", "bedrock"],
                    "description": "The LLM provider to use",
                },
                "system_prompt": {
                    "type": "string",
                    "description": "The system prompt that defines the agent's behavior",
                },
                "user_prompt_template": {
                    "type": "string",
                    "description": "Template for the user prompt. Must contain {news} placeholder",
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether this agent is active and can be used by streams",
                },
            },
            "required": ["name", "provider", "system_prompt", "user_prompt_template"],
        },
    )
    async def add_agent(request):
        """
        Add a new agent entry to the database.

        Args:
            request: The MCP request object containing:
                name: Name of the agent
                description: Optional description of what this agent does
                provider: The LLM provider to use
                system_prompt: The system prompt that defines the agent's behavior
                user_prompt_template: Template for the user prompt
                is_active: Optional flag indicating whether this agent is active

        Returns:
            Dict containing the created agent entry
        """
        try:
            args = request.params.arguments
            name = args.get("name")
            description = args.get("description", "")
            provider = args.get("provider")
            system_prompt = args.get("system_prompt")
            user_prompt_template = args.get("user_prompt_template")
            is_active = args.get("is_active", True)

            # Validate user_prompt_template contains {news} placeholder
            if "{news}" not in user_prompt_template:
                raise McpError(
                    ErrorCode.InvalidParams,
                    "user_prompt_template must contain {news} placeholder",
                )

            # Create agent
            agent = Agent(
                name=name,
                description=description,
                provider=provider,
                system_prompt=system_prompt,
                user_prompt_template=user_prompt_template,
                is_active=is_active,
            )
            agent.save()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": agent.id,
                                "name": agent.name,
                                "description": agent.description,
                                "provider": agent.provider,
                                "system_prompt": agent.system_prompt,
                                "user_prompt_template": agent.user_prompt_template,
                                "is_active": agent.is_active,
                                "created_at": agent.created_at.isoformat(),
                                "updated_at": agent.updated_at.isoformat(),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except ValidationError as e:
            logger.error(f"Validation error adding agent: {str(e)}")
            raise McpError(ErrorCode.InvalidParams, f"Validation error: {str(e)}")
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error adding agent: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error adding agent: {str(e)}")

    @server.tool(
        name="update_agent",
        description="Update an existing agent entry in the database",
        input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the agent to update"},
                "name": {"type": "string", "description": "New name for the agent"},
                "description": {
                    "type": "string",
                    "description": "New description of what this agent does",
                },
                "provider": {
                    "type": "string",
                    "enum": ["openai", "anthropic", "google", "bedrock"],
                    "description": "New LLM provider to use",
                },
                "system_prompt": {
                    "type": "string",
                    "description": "New system prompt that defines the agent's behavior",
                },
                "user_prompt_template": {
                    "type": "string",
                    "description": "New template for the user prompt.",
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether this agent is active and can be used by streams",
                },
            },
            "required": ["id"],
        },
    )
    async def update_agent(request):
        """
        Update an existing agent entry in the database.

        Args:
            request: The MCP request object containing:
                id: ID of the agent to update
                name: Optional new name for the agent
                description: Optional new description of what this agent does
                provider: Optional new LLM provider to use
                system_prompt: Optional new system prompt that defines the agent's behavior
                user_prompt_template: Optional new template for the user prompt
                is_active: Optional new flag indicating whether this agent is active

        Returns:
            Dict containing the updated agent entry
        """
        try:
            args = request.params.arguments
            agent_id = args.get("id")
            name = args.get("name")
            description = args.get("description")
            provider = args.get("provider")
            system_prompt = args.get("system_prompt")
            user_prompt_template = args.get("user_prompt_template")
            is_active = args.get("is_active")

            # Get agent
            try:
                agent = Agent.objects.get(id=agent_id)
            except Agent.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams, f"Agent with id {agent_id} does not exist"
                )

            # Validate user_prompt_template contains {news} placeholder if provided
            has_template = user_prompt_template is not None
            if has_template and "{news}" not in user_prompt_template:
                raise McpError(
                    ErrorCode.InvalidParams,
                    "user_prompt_template must contain {news} placeholder",
                )

            # Update fields if provided
            if name is not None:
                agent.name = name
            if description is not None:
                agent.description = description
            if provider is not None:
                agent.provider = provider
            if system_prompt is not None:
                agent.system_prompt = system_prompt
            if user_prompt_template is not None:
                agent.user_prompt_template = user_prompt_template
            if is_active is not None:
                agent.is_active = is_active

            # Save changes
            agent.save()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "id": agent.id,
                                "name": agent.name,
                                "description": agent.description,
                                "provider": agent.provider,
                                "system_prompt": agent.system_prompt,
                                "user_prompt_template": agent.user_prompt_template,
                                "is_active": agent.is_active,
                                "created_at": agent.created_at.isoformat(),
                                "updated_at": agent.updated_at.isoformat(),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        except ValidationError as e:
            logger.error(f"Validation error updating agent: {str(e)}")
            raise McpError(ErrorCode.InvalidParams, f"Validation error: {str(e)}")
        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error updating agent: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error updating agent: {str(e)}")

    @server.tool(
        name="delete_agent",
        description="Delete an agent entry from the database",
        input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "ID of the agent to delete"},
            },
            "required": ["id"],
        },
    )
    async def delete_agent(request):
        """
        Delete an agent entry from the database.

        Args:
            request: The MCP request object containing:
                id: ID of the agent to delete

        Returns:
            Dict containing success message
        """
        try:
            args = request.params.arguments
            agent_id = args.get("id")

            # Get agent
            try:
                agent = Agent.objects.get(id=agent_id)
            except Agent.DoesNotExist:
                raise McpError(
                    ErrorCode.InvalidParams, f"Agent with id {agent_id} does not exist"
                )

            # Delete agent
            agent.delete()

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": True,
                                "message": f"Agent with id {agent_id} deleted successfully",
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
            logger.error(f"Error deleting agent: {str(e)}")
            raise McpError(ErrorCode.InternalError, f"Error deleting agent: {str(e)}")
