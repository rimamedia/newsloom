from pydantic import Field

from .base_model import BaseConfig


class WebScraperConfig(BaseConfig):
    """Configuration schema for web scraper stream using crawl4ai."""

    class Config:
        """Pydantic configuration class for WebScraperConfig."""

        title = "Web Scraper Configuration"
        json_schema_extra = {
            "example": {
                "batch_size": 10,  # Process 10 empty news articles at a time
            }
        }

    batch_size: int = Field(
        default=10,
        description="Number of empty news articles to process in each batch",
        ge=1,
        le=100,
    )
