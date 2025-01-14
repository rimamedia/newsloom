from pydantic import Field, HttpUrl

from .base_model import BaseConfig


class RSSConfig(BaseConfig):
    url: HttpUrl
    max_items: int = Field(default=10)
