from typing import List, Optional

from pydantic import Field

from .base_model import BaseConfig


class GoogleSearchConfig(BaseConfig):
    """Configuration schema for Google search stream."""

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
    days_ago: Optional[int] = Field(
        default=None,
        description="Filter results from the last X days. Leave empty for no time filter.",
        ge=1,
        le=365,
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
