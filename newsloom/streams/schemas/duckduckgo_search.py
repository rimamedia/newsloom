from typing import Optional

from pydantic import Field

from .base_model import BaseConfig


class DuckDuckGoSearchConfig(BaseConfig):
    """Configuration schema for DuckDuckGo search stream."""

    keywords: str = Field(
        ...,
        description="Search keywords or query",
        example="artificial intelligence news",
    )
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of search results to fetch (1-100)",
        ge=1,
        le=100,
    )
    region: Optional[str] = Field(
        default="wt-wt",
        description="Region for search results (e.g., us-en, uk-en, wt-wt)",
    )
    time_range: Optional[str] = Field(
        default="d",
        description="Time limit for search results: d (day), w (week), m (month)",
    )
    safesearch: Optional[str] = Field(
        default="moderate",
        description="SafeSearch setting: on, moderate, off",
    )
