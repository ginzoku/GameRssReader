from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class RssGateway(ABC):
    """Port: RSS を取得する外部インターフェース（Adapter が実装する）。"""

    @abstractmethod
    def fetch(self, url: str, headers: Optional[Dict] = None) -> List[Dict]:
        """Fetch RSS items from the given URL. Returns list of item dicts."""
        raise NotImplementedError
