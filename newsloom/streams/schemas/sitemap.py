from typing import Annotated

from pydantic import Field, HttpUrl

from .base_model import BaseConfig


class BaseSitemapConfig(BaseConfig):
    sitemap_url: HttpUrl
    max_links: Annotated[int, Field(gt=0, le=1000)] = 100
    follow_next: bool = False
