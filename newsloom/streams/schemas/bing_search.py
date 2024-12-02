from typing import List, Optional

from pydantic import BaseModel, Field


class BingSearchConfig(BaseModel):
    """Configuration schema for Bing search stream."""

    keywords: List[str] = Field(
        ...,
        description="List of keywords to search for",
        example=["climate change", "renewable energy"],
    )
    location: Optional[str] = Field(
        None,
        description="Location to target in search results",
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
