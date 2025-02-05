"""Functions implementing database operations through Claude API."""

import logging
from typing import Dict, Literal, Optional

from sources.models import Source

logger = logging.getLogger(__name__)


def list_sources(limit: Optional[int] = 50, offset: Optional[int] = 0) -> Dict:
    """Get a paginated list of source entries from the database.

    Args:
        limit: Maximum number of entries to return (default 50)
        offset: Number of entries to skip (default 0)

    Returns:
        Dict containing:
            items: List of source entries with their properties
            total: Total number of source entries
            limit: Limit used for query
            offset: Offset used for query
    """
    # Get total count
    total = Source.objects.count()

    # Get paginated results
    items = [
        {
            "id": source.id,
            "name": source.name,
            "link": source.link,
            "type": source.type,
            "created_at": source.created_at.isoformat(),
            "updated_at": source.updated_at.isoformat(),
        }
        for source in Source.objects.all()[offset : offset + limit]
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
