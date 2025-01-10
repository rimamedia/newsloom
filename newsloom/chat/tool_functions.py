"""Functions implementing database operations through Claude API."""

from typing import Dict, List, Literal, Optional

from agents.models import Agent
from mediamanager.models import Media
from sources.models import Source
from streams.models import Stream, StreamLog


def list_media() -> List[Dict]:
    """Get a list of all media entries from the database.

    Returns:
        List[Dict]: List of media entries with their properties
    """
    return [
        {
            "id": media.id,
            "name": media.name,
            "source_ids": list(media.sources.values_list("id", flat=True)),
            "created_at": media.created_at.isoformat(),
            "updated_at": media.updated_at.isoformat(),
        }
        for media in Media.objects.all()
    ]


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


def update_media(
    id: int, name: Optional[str] = None, source_ids: Optional[List[int]] = None
) -> Media:
    """Update an existing media entry in the database.

    Args:
        id: ID of the media to update
        name: Optional new name for the media
        source_ids: Optional list of source IDs to associate with the media

    Returns:
        Media: The updated Media instance

    Raises:
        Media.DoesNotExist: If media with given id doesn't exist
        ValidationError: If validation fails
        Source.DoesNotExist: If any source_id doesn't exist
    """
    try:
        media = Media.objects.get(id=id)
    except Media.DoesNotExist:
        raise Media.DoesNotExist(f"Media with id {id} does not exist")

    if name is not None:
        media.name = name

    if source_ids is not None:
        # Get all sources and validate they exist
        sources = list(Source.objects.filter(id__in=source_ids))
        if len(sources) != len(source_ids):
            raise Source.DoesNotExist("One or more source IDs do not exist")
        media.sources.set(sources)

    media.full_clean()
    media.save()
    return media


def delete_media(id: int) -> None:
    """Delete a media entry from the database.

    Args:
        id: ID of the media to delete

    Raises:
        Media.DoesNotExist: If media with given id doesn't exist
    """
    try:
        media = Media.objects.get(id=id)
        media.delete()
    except Media.DoesNotExist:
        raise Media.DoesNotExist(f"Media with id {id} does not exist")


def list_sources() -> List[Dict]:
    """Get a list of all source entries from the database.

    Returns:
        List[Dict]: List of source entries with their properties
    """
    return [
        {
            "id": source.id,
            "name": source.name,
            "link": source.link,
            "type": source.type,
            "created_at": source.created_at.isoformat(),
            "updated_at": source.updated_at.isoformat(),
        }
        for source in Source.objects.all()
    ]


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


def update_source(
    id: int,
    name: Optional[str] = None,
    link: Optional[str] = None,
    type: Optional[
        Literal["web", "telegram", "search", "rss", "twitter", "facebook", "linkedin"]
    ] = None,
) -> Source:
    """Update an existing source entry in the database.

    Args:
        id: ID of the source to update
        name: Optional new name for the source
        link: Optional new main website URL of the source
        type: Optional new type for the source

    Returns:
        Source: The updated Source instance

    Raises:
        Source.DoesNotExist: If source with given id doesn't exist
        ValidationError: If validation fails
    """
    try:
        source = Source.objects.get(id=id)
    except Source.DoesNotExist:
        raise Source.DoesNotExist(f"Source with id {id} does not exist")

    if name is not None:
        source.name = name
    if link is not None:
        source.link = link
    if type is not None:
        source.type = type

    source.full_clean()
    source.save()
    return source


def delete_source(id: int) -> None:
    """Delete a source entry from the database.

    Args:
        id: ID of the source to delete

    Raises:
        Source.DoesNotExist: If source with given id doesn't exist
    """
    try:
        source = Source.objects.get(id=id)
        source.delete()
    except Source.DoesNotExist:
        raise Source.DoesNotExist(f"Source with id {id} does not exist")


def list_streams(status: Optional[str] = None) -> List[Dict]:
    """Get a list of all stream entries from the database.

    Args:
        status: Optional status to filter streams by

    Returns:
        List[Dict]: List of stream entries with their properties
    """
    queryset = Stream.objects.all()
    if status:
        queryset = queryset.filter(status=status)

    return [
        {
            "id": stream.id,
            "name": stream.name,
            "stream_type": stream.stream_type,
            "source_id": stream.source_id,
            "media_id": stream.media_id,
            "frequency": stream.frequency,
            "configuration": stream.configuration,
            "status": stream.status,
            "last_run": stream.last_run.isoformat() if stream.last_run else None,
            "next_run": stream.next_run.isoformat() if stream.next_run else None,
            "created_at": stream.created_at.isoformat(),
            "updated_at": stream.updated_at.isoformat(),
        }
        for stream in queryset
    ]


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

    from django.utils import timezone

    stream = Stream(
        name=name,
        stream_type=stream_type,
        source=source,
        media=media,
        frequency=frequency,
        configuration=configuration,
        next_run=timezone.now(),  # Set next_run to now when creating
    )
    stream.full_clean()  # This will validate the configuration against schema
    stream.save()
    return stream


def update_stream(
    id: int,
    name: Optional[str] = None,
    stream_type: Optional[
        Literal[
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
        ]
    ] = None,
    frequency: Optional[
        Literal["5min", "15min", "30min", "1hour", "6hours", "12hours", "daily"]
    ] = None,
    configuration: Optional[Dict] = None,
    source_id: Optional[int] = None,
    media_id: Optional[int] = None,
    status: Optional[Literal["active", "paused", "failed", "processing"]] = None,
) -> Stream:
    """Update an existing stream entry in the database.

    Args:
        id: ID of the stream to update
        name: Optional new name for the stream
        stream_type: Optional new type for the stream
        frequency: Optional new frequency for the stream
        configuration: Optional new configuration parameters
        source_id: Optional new source ID to associate with the stream
        media_id: Optional new media ID to associate with the stream
        status: Optional new status for the stream

    Returns:
        Stream: The updated Stream instance

    Raises:
        Stream.DoesNotExist: If stream with given id doesn't exist
        ValidationError: If validation fails
        Source.DoesNotExist: If source_id is provided but doesn't exist
        Media.DoesNotExist: If media_id is provided but doesn't exist
    """
    try:
        stream = Stream.objects.get(id=id)
    except Stream.DoesNotExist:
        raise Stream.DoesNotExist(f"Stream with id {id} does not exist")

    if name is not None:
        stream.name = name
    if stream_type is not None:
        stream.stream_type = stream_type
    if frequency is not None:
        stream.frequency = frequency
    if configuration is not None:
        stream.configuration = configuration
    if status is not None:
        stream.status = status

    # Update source if source_id provided
    if source_id is not None:
        if source_id == 0:  # Special case to remove source
            stream.source = None
        else:
            try:
                stream.source = Source.objects.get(id=source_id)
            except Source.DoesNotExist:
                raise Source.DoesNotExist(f"Source with id {source_id} does not exist")

    # Update media if media_id provided
    if media_id is not None:
        if media_id == 0:  # Special case to remove media
            stream.media = None
        else:
            try:
                stream.media = Media.objects.get(id=media_id)
            except Media.DoesNotExist:
                raise Media.DoesNotExist(f"Media with id {media_id} does not exist")

    from django.utils import timezone

    # Set next_run to now when updating
    stream.next_run = timezone.now()

    stream.full_clean()
    stream.save()
    return stream


def delete_stream(id: int) -> None:
    """Delete a stream entry from the database.

    Args:
        id: ID of the stream to delete

    Raises:
        Stream.DoesNotExist: If stream with given id doesn't exist
    """
    try:
        stream = Stream.objects.get(id=id)
        stream.delete()
    except Stream.DoesNotExist:
        raise Stream.DoesNotExist(f"Stream with id {id} does not exist")


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


def get_stream_logs(
    stream_id: Optional[int] = None,
    status: Optional[Literal["success", "failed", "running"]] = None,
    limit: Optional[int] = 100,
) -> List[Dict]:
    """Get stream execution logs filtered by stream ID and/or status.

    Args:
        stream_id: Optional ID of the stream to get logs for
        status: Optional status to filter logs by
        limit: Optional maximum number of logs to return (default 100)

    Returns:
        List[Dict]: List of stream log entries with their properties

    Raises:
        Stream.DoesNotExist: If stream_id is provided but doesn't exist
    """
    # Validate stream_id if provided
    if stream_id:
        try:
            Stream.objects.get(id=stream_id)
        except Stream.DoesNotExist:
            raise Stream.DoesNotExist(f"Stream with id {stream_id} does not exist")

    # Build query
    queryset = StreamLog.objects.all()
    if stream_id:
        queryset = queryset.filter(stream_id=stream_id)
    if status:
        queryset = queryset.filter(status=status)

    # Get latest logs first
    queryset = queryset.order_by("-started_at")[:limit]

    return [
        {
            "id": log.id,
            "stream_id": log.stream_id,
            "status": log.status,
            "started_at": log.started_at.isoformat(),
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "error_message": log.error_message,
            "result": log.result,
        }
        for log in queryset
    ]
