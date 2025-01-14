from pydantic import Field, HttpUrl

from . import BaseConfig


class RSSConfig(BaseConfig):
    url: HttpUrl
    max_items: int = Field(default=10)
