from typing import Annotated, List, Optional

from pydantic import Field, field_validator

from . import BaseConfig


class TelegramConfig(BaseConfig):
    channel_id: str
    limit: Annotated[int, Field(gt=0, le=100)] = 50
    include_media: bool = True

    @field_validator("channel_id")
    def validate_channel_id(cls, v):
        v = v.strip()
        if not v.startswith("-100"):
            raise ValueError("Channel ID must start with -100")
        if not v[4:].isdigit():
            raise ValueError("Channel ID must be numeric after -100")
        return v


class TelegramPublishConfig(BaseConfig):
    channel_id: str
    batch_size: Annotated[int, Field(gt=0, le=50)] = 10
    bot_token: str
    time_window_minutes: Annotated[int, Field(gt=0, le=1440)] = 10  # max 24 hours
    source_types: Optional[List[str]] = Field(
        None,
        description=(
            "Optional list of source types to filter news by (e.g. ['web', 'telegram']). "
            "If not provided, all types will be included."
        ),
    )

    @field_validator("channel_id")
    def validate_channel_id(cls, v):
        v = v.strip()
        if not v.startswith("-100"):
            raise ValueError("Channel ID must start with -100")
        if not v[4:].isdigit():
            raise ValueError("Channel ID must be numeric after -100")
        return v

    @field_validator("bot_token")
    def validate_bot_token(cls, v):
        if not v.strip():
            raise ValueError("Bot token cannot be empty")
        return v.strip()


class TelegramBulkParserConfig(BaseConfig):
    """Configuration schema for bulk Telegram channel parsing."""

    time_window_minutes: Annotated[int, Field(gt=0, le=1440)] = 60  # max 24 hours
    max_scrolls: Annotated[int, Field(gt=0, le=100)] = 20
    wait_time: Annotated[int, Field(gt=0, le=30)] = 10
