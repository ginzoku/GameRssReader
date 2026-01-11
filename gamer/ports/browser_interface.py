from abc import ABC, abstractmethod
from typing import Any

class BrowserInterface(ABC):
    @abstractmethod
    def embed_or_open(self, ui_host: Any, url: str) -> bool:
        """Try to embed the given URL into the UI host; if not possible, open externally.
        Return True if the URL was embedded (or handled) without falling back to external open.
        """
        raise NotImplementedError()

    @abstractmethod
    def open_external(self, url: str) -> None:
        raise NotImplementedError()
