from pydantic import BaseModel, Field, HttpUrl


class RSSConfig(BaseModel):
    url: HttpUrl
    max_items: int = Field(default=10)

    class Config:
        """Configuration for RSS Feed schema validation."""

        extra = "forbid"
