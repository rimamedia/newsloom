from pydantic import BaseModel, HttpUrl


class ArticleSearcherConfig(BaseModel):
    url: HttpUrl
    link_selector: str
    link_selector_type: str = "css"
    article_selector: str
    article_selector_type: str = "css"
    search_text: str
    max_links: int = 10

    model_config = {"extra": "forbid"}
