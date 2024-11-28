from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class PlaywrightConfig(BaseModel):
    url: HttpUrl
    link_selector: str
    max_links: Annotated[int, Field(gt=0, le=1000)] = 100

    class Config:
        """Configuration for Playwright schema validation."""

        extra = "forbid"
