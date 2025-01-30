"""Functions implementing database operations through Claude API."""

import logging
from typing import Dict, List, Literal, Optional

from agents.models import Agent

logger = logging.getLogger(__name__)


def list_agents(is_active: Optional[bool] = None) -> List[Dict]:
    """Get a list of all agent entries from the database.

    Args:
        is_active: Optional flag to filter agents by active status

    Returns:
        List[Dict]: List of agent entries with their properties
    """
    queryset = Agent.objects.all()
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    return [
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
        }
        for agent in queryset
    ]


def add_agent(
    name: str,
    provider: Literal["openai", "anthropic", "google", "bedrock"],
    system_prompt: str,
    user_prompt_template: str,
    description: Optional[str] = None,
    is_active: Optional[bool] = True,
) -> Agent:
    """Add a new agent entry to the database.

    Args:
        name: Name of the agent
        provider: The LLM provider to use
        system_prompt: The system prompt that defines the agent's behavior
        user_prompt_template: Template for the user prompt. Must contain {news} placeholder
        description: Optional description of what this agent does
        is_active: Optional flag indicating whether this agent is active

    Returns:
        Agent: The created Agent instance

    Raises:
        ValidationError: If validation fails or if user_prompt_template
        doesn't contain {news} placeholder
    """
    agent = Agent(
        name=name,
        provider=provider,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        description=description or "",
        is_active=is_active,
    )
    agent.full_clean()  # This will validate the prompt template contains {news}
    agent.save()
    return agent


def update_agent(
    id: int,
    name: Optional[str] = None,
    provider: Optional[Literal["openai", "anthropic", "google", "bedrock"]] = None,
    system_prompt: Optional[str] = None,
    user_prompt_template: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Agent:
    """Update an existing agent entry in the database.

    Args:
        id: ID of the agent to update
        name: Optional new name for the agent
        provider: Optional new LLM provider to use
        system_prompt: Optional new system prompt
        user_prompt_template: Optional new user prompt template
        description: Optional new description
        is_active: Optional new active status

    Returns:
        Agent: The updated Agent instance

    Raises:
        Agent.DoesNotExist: If agent with given id doesn't exist
        ValidationError: If validation fails or if user_prompt_template
        doesn't contain {news} placeholder
    """
    try:
        agent = Agent.objects.get(id=id)
    except Agent.DoesNotExist:
        raise Agent.DoesNotExist(f"Agent with id {id} does not exist")

    if name is not None:
        agent.name = name
    if provider is not None:
        agent.provider = provider
    if system_prompt is not None:
        agent.system_prompt = system_prompt
    if user_prompt_template is not None:
        agent.user_prompt_template = user_prompt_template
    if description is not None:
        agent.description = description
    if is_active is not None:
        agent.is_active = is_active

    agent.full_clean()  # This will validate the prompt template contains {news}
    agent.save()
    return agent


def delete_agent(id: int) -> None:
    """Delete an agent entry from the database.

    Args:
        id: ID of the agent to delete

    Raises:
        Agent.DoesNotExist: If agent with given id doesn't exist
    """
    try:
        agent = Agent.objects.get(id=id)
        agent.delete()
    except Agent.DoesNotExist:
        raise Agent.DoesNotExist(f"Agent with id {id} does not exist")
