from pydantic import Field

from .base_model import BaseConfig


class DocPublisherConfig(BaseConfig):
    """Configuration schema for doc publisher task.

    Defines the configuration for publishing docs to a Telegram channel. The task processes
    unpublished docs (those with 'new' or 'failed' status) from a media source and sends
    them to the specified Telegram channel. Docs are processed in batches to prevent
    system overload.

    The task will:
    - Process docs in order of creation date
    - Send each doc's title (in bold), text, and link to Telegram
    - Update doc status to 'publish' on success
    - Create publish logs for tracking
    - Handle failures by marking docs as 'failed' for retry
    """

    channel_id: str = Field(
        ...,
        description="Telegram channel ID where docs will be published",
        example="-100123456789",
    )
    bot_token: str = Field(
        ...,
        description="Telegram bot token for authentication",
        example="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
    )
    batch_size: int = Field(
        default=10,
        description="Maximum number of docs to process in one batch",
        ge=1,
        le=100,
    )
    google_doc_links: bool = Field(
        default=False,
        description="Whether to include Google Doc links in messages",
    )
