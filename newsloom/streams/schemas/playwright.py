from typing import Annotated

from pydantic import Field, HttpUrl

from .base_model import BaseConfig


class PlaywrightConfig(BaseConfig):
    url: HttpUrl
    link_selector: str
    max_links: Annotated[int, Field(gt=0, le=1000)] = 100
