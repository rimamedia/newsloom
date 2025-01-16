from pydantic import BaseModel, Field


class GoogleDocCreatorConfig(BaseModel):
    """Configuration schema for Google Doc creator stream."""

    template_id: str | None = Field(
        default=None,
        description="Optional Google Doc template ID to use as base for new documents",
    )
    folder_id: str = Field(
        ...,
        description="Google Drive folder ID where to create new documents",
    )
    service_account_path: str = Field(
        default="credentials.json",
        description="Path to the Google service account credentials JSON file",
    )
