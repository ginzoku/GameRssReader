from abc import ABC, abstractmethod


class WebViewPort(ABC):
    """Port: 抽象 WebView インターフェース"""

    @abstractmethod
    def load(self, url: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_html(self, html: str, base_url: str = "about:blank") -> None:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError
