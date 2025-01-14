from pydantic import HttpUrl

from . import BaseConfig


class ArticleSearcherConfig(BaseConfig):
    url: HttpUrl
    link_selector: str
    link_selector_type: str = "css"
    article_selector: str
    article_selector_type: str = "css"
    search_text: str
    max_links: int = 10
