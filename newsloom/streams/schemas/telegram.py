from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class TelegramConfig(BaseModel):
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

    class Config:
        """Configuration for Telegram schema validation."""

        extra = "forbid"


class TelegramPublishConfig(BaseModel):
    channel_id: str
    batch_size: Annotated[int, Field(gt=0, le=50)] = 10
    bot_token: str
    time_window_minutes: Annotated[int, Field(gt=0, le=1440)] = 10  # max 24 hours

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

    class Config:
        """Configuration for Telegram Publisher schema validation."""

        extra = "forbid"


class TelegramTestConfig(BaseModel):
    """Configuration schema for Telegram test task."""

    channel_id: str
    bot_token: str

    class Config:
        """Configuration for schema validation."""

        extra = "forbid"


class TelegramBulkParserConfig(BaseModel):
    """Configuration schema for bulk Telegram channel parsing."""

    time_window_minutes: Annotated[int, Field(gt=0, le=1440)] = 60  # max 24 hours
    max_scrolls: Annotated[int, Field(gt=0, le=100)] = 20
    wait_time: Annotated[int, Field(gt=0, le=30)] = 10

    class Config:
        """Configuration for schema validation."""

        extra = "forbid"
