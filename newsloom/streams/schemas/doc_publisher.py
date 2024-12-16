from pydantic import BaseModel, Field


class DocPublisherConfig(BaseModel):
    """Configuration schema for doc publisher task."""

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
    time_window_minutes: int = Field(
        default=60,
        description="Time window in minutes to look back for docs",
        ge=1,
        le=1440,  # Max 24 hours
    )
    batch_size: int = Field(
        default=10,
        description="Maximum number of docs to process in one batch",
        ge=1,
        le=100,
    )
