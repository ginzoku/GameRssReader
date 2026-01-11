from abc import ABC, abstractmethod
from typing import List
from gamer.domain.entities import Article

class RSSProvider(ABC):
    @abstractmethod
    def fetch_rss(self, url: str) -> List[Article]:
        raise NotImplementedError()

    @abstractmethod
    def fetch_article(self, url: str) -> Article:
        raise NotImplementedError()

    @abstractmethod
    def fetch_full_article(self, url: str) -> Article:
        raise NotImplementedError()
