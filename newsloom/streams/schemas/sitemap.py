from typing import Annotated
from pydantic import BaseModel, HttpUrl, Field

class BaseSitemapConfig(BaseModel):
    sitemap_url: HttpUrl
    max_links: Annotated[int, Field(gt=0, le=1000)] = 100
    follow_next: bool = False
    
    class Config:
        extra = 'forbid' 