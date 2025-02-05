"""Functions implementing database operations through Claude API."""

import logging
from typing import Dict, List, Literal, Optional

from mediamanager.models import Media
from sources.models import Source
from streams.models import Stream, StreamLog

logger = logging.getLogger(__name__)


def list_streams(
    status: Optional[str] = None, limit: Optional[int] = 50, offset: Optional[int] = 0
) -> Dict:
    """Get a paginated list of stream entries from the database.

    Args:
        status: Optional status to filter streams by
        limit: Maximum number of entries to return (default 50)
        offset: Number of entries to skip (default 0)

    Returns:
        Dict containing:
            items: List of stream entries with their properties
            total: Total number of streams matching the filter
            limit: Limit used for query
            offset: Offset used for query
    """
    # Build base queryset
    queryset = Stream.objects.all()
    if status:
        queryset = queryset.filter(status=status)

    # Get total count
    total = queryset.count()

    # Get paginated results
    items = [
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
        for stream in queryset[offset : offset + limit]
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
