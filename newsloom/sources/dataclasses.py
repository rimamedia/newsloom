from dataclasses import dataclass
from datetime import datetime


@dataclass
class Link:
    link: str
    title: str | None = None
    text: str | None = None
    published_at: datetime | None = None
