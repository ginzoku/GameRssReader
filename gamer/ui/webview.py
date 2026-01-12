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
        # simple wrapper: allow optional automatic horizontal centering on load
        self._center_horizontal = True
        try:
            self.view.loadFinished.connect(self._on_load_finished)
        except Exception:
            pass

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

    def _on_load_finished(self, ok: bool):
        if not ok:
            return
        if not self._center_horizontal:
            return
        js = '''(function(){
            try{
                var w = window.innerWidth || document.documentElement.clientWidth;
                var sw = document.documentElement.scrollWidth || document.body.scrollWidth || 0;
                var target = Math.max(0, Math.floor((sw - w) / 2));
                window.scrollTo(target, 0);
            }catch(e){ /* ignore */ }
        })();'''
        try:
            page = self.view.page()
            page.runJavaScript(js)
        except Exception:
            pass

    def clear(self) -> None:
        try:
            # navigate to about:blank
            self.view.load(QtCore.QUrl("about:blank"))
        except Exception:
            pass

    def set_center_horizontal(self, enable: bool) -> None:
        """Enable/disable automatic horizontal centering after page load."""
        self._center_horizontal = bool(enable)
