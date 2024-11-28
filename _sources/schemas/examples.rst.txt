Schema Examples
=============

This guide provides examples of different schema implementations in NewLoom.

Sitemap Schema
------------

Example of a sitemap configuration schema:

.. code-block:: python

    from pydantic import BaseModel, HttpUrl, Field
    
    class SitemapConfig(BaseModel):
        sitemap_url: HttpUrl
        max_links: int = Field(gt=0, le=1000, default=100)
        follow_next: bool = False
        
        class Config:
            extra = 'forbid'

Playwright Schema
--------------

Example of a Playwright configuration schema:

.. code-block:: python

    class PlaywrightConfig(BaseModel):
        url: HttpUrl
        link_selector: str
        max_links: int = Field(gt=0, le=1000, default=100)
        wait_for: Optional[str] = None
        
        @field_validator('link_selector')
        def validate_selector(cls, v):
            if not v.strip():
                raise ValueError("Selector cannot be empty")
            return v

RSS Feed Schema
------------

Example of an RSS feed configuration schema:

.. code-block:: python

    class RSSFeedConfig(BaseModel):
        feed_url: HttpUrl
        max_items: int = Field(gt=0, le=500, default=50)
        include_summary: bool = True
        update_interval: int = Field(
            gt=0, 
            le=24*60, 
            default=60,
            description="Update interval in minutes"
        )

Telegram Schema
------------

Example of a Telegram configuration schema:

.. code-block:: python

    class TelegramConfig(BaseModel):
        channel_name: str
        limit: int = Field(gt=0, le=100, default=50)
        include_media: bool = True
        
        @field_validator('channel_name')
        def validate_channel_name(cls, v):
            if not v.strip().startswith('@'):
                raise ValueError("Channel name must start with @")
            return v 