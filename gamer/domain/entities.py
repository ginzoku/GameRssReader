from dataclasses import dataclass
from typing import Optional

@dataclass
class Article:
    title: str
    link: str
    description: Optional[str] = None
    pubDate: Optional[str] = None
    body: Optional[str] = None
