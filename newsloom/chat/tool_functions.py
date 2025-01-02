"""Functions implementing database operations through Claude API."""

from typing import Dict, List, Literal, Optional

from agents.models import Agent
from mediamanager.models import Media
from sources.models import Source
from streams.models import Stream


def add_media(name: str, source_ids: Optional[List[int]] = None) -> Media:
    """Add a new media entry to the database.

    Args:
        name: Name of the media
        source_ids: Optional list of source IDs to associate with the media

    Returns:
        Media: The created Media instance

    Raises:
        ValidationError: If validation fails
        Source.DoesNotExist: If any source_id doesn't exist
    """
    media = Media.objects.create(name=name)

    if source_ids:
        # Get all sources and validate they exist
        sources = list(Source.objects.filter(id__in=source_ids))
        if len(sources) != len(source_ids):
            raise Source.DoesNotExist("One or more source IDs do not exist")

        media.sources.set(sources)

    return media


def add_source(
    name: str,
    link: str,
    type: Literal[
        "web", "telegram", "search", "rss", "twitter", "facebook", "linkedin"
    ],
) -> Source:
    """Add a new source entry to the database.

    Args:
        name: Name of the source
        link: Main website URL of the source
        type: Type of the source

    Returns:
        Source: The created Source instance

    Raises:
        ValidationError: If validation fails
    """
    source = Source(name=name, link=link, type=type)
    source.full_clean()  # Validate the model
    source.save()
    return source


def add_stream(
    name: str,
    stream_type: Literal[
        "sitemap_news",
        "sitemap_blog",
        "playwright_link_extractor",
        "rss_feed",
        "web_article",
        "telegram_channel",
        "telegram_publish",
        "telegram_test",
        "article_searcher",
        "bing_search",
        "google_search",
        "telegram_bulk_parser",
        "news_stream",
        "doc_publisher",
        "articlean",
    ],
    frequency: Literal["5min", "15min", "30min", "1hour", "6hours", "12hours", "daily"],
    configuration: Dict,
    source_id: Optional[int] = None,
    media_id: Optional[int] = None,
) -> Stream:
    """Add a new stream entry to the database.

    Args:
        name: Name of the stream
        stream_type: Type of the stream
        frequency: How often the stream should run
        configuration: Stream-specific configuration parameters
        source_id: Optional ID of the source to associate with the stream
        media_id: Optional ID of the media to associate with the stream

    Returns:
        Stream: The created Stream instance

    Raises:
        ValidationError: If validation fails
        Source.DoesNotExist: If source_id is provided but doesn't exist
        Media.DoesNotExist: If media_id is provided but doesn't exist
    """
    # Validate source_id if provided
    source = None
    if source_id:
        try:
            source = Source.objects.get(id=source_id)
        except Source.DoesNotExist:
            raise Source.DoesNotExist(f"Source with id {source_id} does not exist")

    # Validate media_id if provided
    media = None
    if media_id:
        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            raise Media.DoesNotExist(f"Media with id {media_id} does not exist")

    stream = Stream(
        name=name,
        stream_type=stream_type,
        source=source,
        media=media,
        frequency=frequency,
        configuration=configuration,
    )
    stream.full_clean()  # This will validate the configuration against schema
    stream.save()
    return stream


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
