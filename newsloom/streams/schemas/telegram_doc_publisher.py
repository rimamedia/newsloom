from pydantic import BaseModel, Field


class TelegramDocPublisherConfig(BaseModel):
    """Configuration schema for Telegram doc publisher stream."""

    message_template: str = Field(
        default="{title}\n\n{google_doc_link}",
        description="Template for the message to be sent to Telegram. Available variables: {title}, {google_doc_link}",  # noqa E501
    )
    batch_size: int = Field(
        default=10,
        description="Maximum number of docs to publish in one run",
        ge=1,
        le=100,
    )
    delay_between_messages: int = Field(
        default=2,
        description="Delay in seconds between messages to avoid rate limiting",
        ge=1,
        le=60,
    )
