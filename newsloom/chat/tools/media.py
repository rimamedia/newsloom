import logging
from typing import Dict, List, Optional

from mediamanager.models import Media
from sources.models import Source

logger = logging.getLogger(__name__)


def list_media(limit: Optional[int] = 50, offset: Optional[int] = 0) -> Dict:
    """Get a paginated list of media entries from the database.

    Args:
        limit: Maximum number of entries to return (default 50)
        offset: Number of entries to skip (default 0)

    Returns:
        Dict containing:
            items: List of media entries with their properties
            total: Total number of media entries
            limit: Limit used for query
            offset: Offset used for query
    """
    # Get total count
    total = Media.objects.count()

    # Get paginated results
    items = [
        {
            "id": media.id,
            "name": media.name,
            "source_ids": list(media.sources.values_list("id", flat=True)),
            "created_at": media.created_at.isoformat(),
            "updated_at": media.updated_at.isoformat(),
        }
        for media in Media.objects.all()[offset : offset + limit]
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
