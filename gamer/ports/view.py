from abc import ABC, abstractmethod
from typing import List, Dict


class ViewPort(ABC):
    """Port: View が満たすべきインターフェース（Presenter が利用する）。"""

    @abstractmethod
    def show_status(self, message: str, timeout_ms: int = 0) -> None:
        raise NotImplementedError

    @abstractmethod
    def show_list(self, items: List[Dict]) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_url(self, url: str) -> None:
        raise NotImplementedError
