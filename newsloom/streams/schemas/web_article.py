from typing import Dict, Optional
from pydantic import BaseModel, HttpUrl, field_validator

class WebArticleConfig(BaseModel):
    base_url: HttpUrl
    selectors: Dict[str, str]
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