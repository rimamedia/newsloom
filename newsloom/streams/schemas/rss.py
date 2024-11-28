from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class RSSFeedConfig(BaseModel):
    feed_url: HttpUrl
    max_items: Annotated[int, Field(gt=0, le=500)] = 50
    include_summary: bool = True

    class Config:
        """Configuration for RSS Feed schema validation."""

        extra = "forbid"
