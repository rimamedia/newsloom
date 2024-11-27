from typing import Annotated
from pydantic import BaseModel, Field, field_validator

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

class TelegramPublishConfig(BaseModel):
    channel_name: str
    batch_size: Annotated[int, Field(gt=0, le=50)] = 10
    
    @field_validator('channel_name')
    def validate_channel_name(cls, v):
        if not v.strip().startswith('@'):
            raise ValueError("Channel name must start with @")
        return v
    
    class Config:
        extra = 'forbid' 