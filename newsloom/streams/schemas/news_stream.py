from typing import Optional

from pydantic import Field

from . import BaseConfig


class NewsStreamConfig(BaseConfig):
    agent_id: int = Field(..., description="ID of the agent to use for processing news")
    time_window_minutes: int = Field(
        60,
        description="Time window in minutes to look back for news (default: 1 hour)",
    )
    max_items: Optional[int] = Field(
        100, description="Maximum number of news items to process (default: 100)"
    )
    save_to_docs: bool = Field(
        True, description="Whether to save the processed output to docs"
    )
