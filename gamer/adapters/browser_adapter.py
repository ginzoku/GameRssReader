import webbrowser
from typing import Any

try:
    import webview
except Exception:
    webview = None

from gamer.ports.browser_interface import BrowserInterface


class DefaultBrowserAdapter(BrowserInterface):
    """Simple adapter that prefers embedding via pywebview if available,
    falls back to UI-provided embed helpers, then to external browser.
    """

    def embed_or_open(self, ui_host: Any, url: str) -> bool:
        # If ui_host provides a pywebview embed helper, try it
        try:
            if hasattr(ui_host, 'embed_pywebview_into_frame') and webview is not None:
                ok = ui_host.embed_pywebview_into_frame(url)
                if ok:
                    return True
        except Exception:
            pass

        # If ui_host provides a CEF embed helper, try it
        try:
            if hasattr(ui_host, 'create_browser_embedded'):
                try:
                    ui_host.create_browser_embedded(url)
                    return True
                except Exception:
                    pass
        except Exception:
            pass

        # Last resort: open external
        self.open_external(url)
        return False

    def open_external(self, url: str) -> None:
        webbrowser.open(url)


# exported instance
default_browser_adapter = DefaultBrowserAdapter()
