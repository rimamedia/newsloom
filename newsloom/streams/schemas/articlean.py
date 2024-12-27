from pydantic import BaseModel, HttpUrl


class ArticleanConfiguration(BaseModel):
    """Configuration for the Articlean task."""

    endpoint: HttpUrl
    token: str
