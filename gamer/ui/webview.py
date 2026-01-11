from typing import Optional

from PySide6 import QtCore
from PySide6.QtWebEngineWidgets import QWebEngineView

from ..ports.webview import WebViewPort


class QtWebViewWrapper(WebViewPort):
    """Wrapper around QWebEngineView implementing WebViewPort."""

    def __init__(self, view: Optional[QWebEngineView] = None):
        if view is None:
            self.view = QWebEngineView()
        else:
            self.view = view

    def load(self, url: str) -> None:
        try:
            self.view.load(QtCore.QUrl(url))
        except Exception:
            # swallow to keep presenter resilient
            pass

    def set_html(self, html: str, base_url: str = "about:blank") -> None:
        try:
            page = self.view.page()
            page.setHtml(html, QtCore.QUrl(base_url))
        except Exception:
            pass

    def clear(self) -> None:
        try:
            # navigate to about:blank
            self.view.load(QtCore.QUrl("about:blank"))
        except Exception:
            pass
