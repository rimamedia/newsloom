from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class RSSFeedConfig(BaseModel):
    feed_url: HttpUrl
    max_entries: Annotated[int, Field(gt=0, le=500)] = 100

    class Config:
        """Configuration for RSS Feed schema validation."""

        extra = "forbid"
