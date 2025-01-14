from typing import List

from pydantic import Field

from .base_model import BaseConfig


class BingSearchConfig(BaseConfig):
    """Configuration schema for Bing search stream."""

    keywords: List[str] = Field(
        ...,
        description="List of keywords to search for",
        example=["climate change", "renewable energy"],
    )
    max_results_per_keyword: int = Field(
        default=5,
        description="Maximum number of results to fetch per keyword",
        ge=1,
        le=50,
    )
    search_type: str = Field(
        default="news",
        description="Type of search to perform",
        enum=["news", "web"],
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode with visible browser and additional logging",
    )
