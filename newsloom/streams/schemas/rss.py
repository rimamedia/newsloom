from typing import Annotated
from pydantic import BaseModel, HttpUrl, Field

class RSSFeedConfig(BaseModel):
    feed_url: HttpUrl
    max_items: Annotated[int, Field(gt=0, le=500)] = 50
    include_summary: bool = True
    
    class Config:
        extra = 'forbid' 