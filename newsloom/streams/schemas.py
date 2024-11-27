from typing import Dict, Any, Optional, Annotated
from pydantic import BaseModel, HttpUrl, conint, field_validator, Field

class BaseSitemapConfig(BaseModel):
    sitemap_url: HttpUrl
    max_links: Annotated[int, Field(gt=0, le=1000)] = 100
    follow_next: bool = False
    
    class Config:
        extra = 'forbid'  # Prevent additional fields

class RSSFeedConfig(BaseModel):
    feed_url: HttpUrl
    max_items: Annotated[int, Field(gt=0, le=500)] = 50
    include_summary: bool = True
    
    class Config:
        extra = 'forbid'

class WebArticleConfig(BaseModel):
    base_url: HttpUrl
    selectors: Dict[str, str]  # CSS selectors for different elements
    pagination: Optional[Dict[str, str]] = None
    
    @field_validator('selectors')
    def validate_selectors(cls, v):
        required_selectors = {'title', 'content'}
        if not all(key in v for key in required_selectors):
            missing = required_selectors - v.keys()
            raise ValueError(f"Missing required selectors: {missing}")
        return v
    
    class Config:
        extra = 'forbid'

class TelegramConfig(BaseModel):
    channel_name: str
    limit: Annotated[int, Field(gt=0, le=100)] = 50
    include_media: bool = True
    
    @field_validator('channel_name')
    def validate_channel_name(cls, v):
        if not v.strip().startswith('@'):
            raise ValueError("Channel name must start with @")
        return v
    
    class Config:
        extra = 'forbid'

class PlaywrightConfig(BaseModel):
    url: HttpUrl
    link_selector: str
    max_links: Annotated[int, Field(gt=0, le=1000)] = 100
    
    class Config:
        extra = 'forbid'

# Map stream types to their configuration schemas
STREAM_CONFIG_SCHEMAS = {
    'playwright_link_extractor': PlaywrightConfig,
    'sitemap_news': BaseSitemapConfig,
    'sitemap_blog': BaseSitemapConfig,
    'rss_feed': RSSFeedConfig,
    'web_article': WebArticleConfig,
    'telegram_channel': TelegramConfig,
} 