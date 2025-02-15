from pydantic import BaseModel, Field


class GoogleDocCreatorConfig(BaseModel):
    """Configuration schema for Google Doc creator stream."""

    template_id: str | None = Field(
        default=None,
        description="Optional Google Doc template ID to use as base for new documents",
    )
    folder_id: str = Field(
        ...,
        description="Google Drive folder ID where documents will be created. Must be shared with the service account.",  # noqa E501
    )
