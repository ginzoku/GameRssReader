import threading
from typing import Optional

from ..ports.rss_gateway import RssGateway
from ..ports.view import ViewPort


class FeedPresenter:
    def __init__(self, view: ViewPort, rss_url: str, headers: Optional[dict] = None, rss_gateway: Optional[RssGateway] = None):
        self.view = view
        self.rss_url = rss_url
        self.headers = headers or {"User-Agent": "4games-scraper/1.0 (+https://example.com)"}
        self.rss_gateway = rss_gateway

    def _emit_status(self, msg: str, timeout: int = 0):
        # Prefer port method, fallback to Qt signals if present
        try:
            self.view.show_status(msg, timeout)
            return
        except Exception:
            pass
        try:
            self.view.status_message.emit(msg, timeout)
        except Exception:
            pass

    def _emit_list(self, items):
        try:
            self.view.show_list(items)
            return
        except Exception:
            pass
        try:
            self.view.list_ready.emit(items)
        except Exception:
            pass

    def load_feed(self):
        def _run():
            try:
                self._emit_status('RSS を取得中…', 0)
                if self.rss_gateway:
                    items = self.rss_gateway.fetch(self.rss_url, headers=self.headers)
                else:
                    from ..adapters.rss_adapter import fetch_rss
                    items = fetch_rss(self.rss_url, headers=self.headers)
                self._emit_list(items)
                self._emit_status('RSS を取得しました', 3000)
            except Exception as e:
                self._emit_status(f'RSS 取得エラー: {e}', 5000)

        threading.Thread(target=_run, daemon=True).start()

    def load_feed_sync(self):
        """Synchronous version of feed loading for tests."""
        try:
            self._emit_status('RSS を取得中…', 0)
            if self.rss_gateway:
                items = self.rss_gateway.fetch(self.rss_url, headers=self.headers)
            else:
                from ..adapters.rss_adapter import fetch_rss
                items = fetch_rss(self.rss_url, headers=self.headers)
            self._emit_list(items)
            self._emit_status('RSS を取得しました', 3000)
            return items
        except Exception as e:
            self._emit_status(f'RSS 取得エラー: {e}', 5000)
            raise

    def select(self, index: int):
        try:
            if index < 0:
                return
            items = getattr(self.view, 'items', None)
            if not items or index >= len(items):
                return
            link = items[index].get('link')
            if link:
                try:
                    self.view.load_url(link)
                except Exception:
                    # fallback to view.webview if available
                    try:
                        self.view.webview.load(link)
                    except Exception:
                        pass
        except Exception:
            pass

