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

    def load_feed(self, force: bool = False):
        def _run(force_local: bool = force):
            try:
                self._emit_status('RSS を取得中…', 0)
                if self.rss_gateway:
                    # allow gateway-based fetch to accept robots override when forced
                    try:
                        items = self.rss_gateway.fetch(self.rss_url, headers=self.headers)
                    except TypeError:
                        # older adapters may not accept allow_robots arg
                        items = self.rss_gateway.fetch(self.rss_url, headers=self.headers)
                else:
                    # Special-case: Automaton category/search pages
                    try:
                        if 'automaton-media.com' in (self.rss_url or ''):
                            from ..utils.automaton_url_parser import AutomatonUrlParser
                            # use the post-310463-specific extractor to limit scope
                            try:
                                parsed = AutomatonUrlParser.extract_post310463_articles(self.rss_url, headers=self.headers, allow_robots=force_local)
                                items = [
                                    {'title': (p.get('title') or '').strip() or p.get('url'), 'link': p.get('url'), 'pubDate': '', 'description': ''}
                                    for p in parsed
                                ]
                            except PermissionError:
                                # robots.txt disallows fetching this page
                                self._emit_status('robots.txt により取得が拒否されました: ' + self.rss_url, 5000)
                                items = []
                                # ask UI to prompt override (UI will call load_feed(force=True) if user accepts)
                                try:
                                    if hasattr(self.view, 'prompt_robots_override'):
                                        self.view.prompt_robots_override(self.rss_url)
                                except Exception:
                                    pass
                        elif 'gamespark.jp' in (self.rss_url or '') and '/category/' in (self.rss_url or ''):
                            from ..utils.gamespark_url_parser import GameSparkUrlParser
                            try:
                                parsed = GameSparkUrlParser.extract_article_links(self.rss_url, headers=self.headers, include_alt=True, allow_robots=force_local)
                                items = [
                                    {'title': (p.get('alt') or '').strip() or p.get('url'), 'link': p.get('url'), 'pubDate': '', 'description': ''}
                                    for p in parsed
                                ]
                            except PermissionError:
                                self._emit_status('robots.txt により取得が拒否されました: ' + self.rss_url, 5000)
                                items = []
                                try:
                                    if hasattr(self.view, 'prompt_robots_override'):
                                        self.view.prompt_robots_override(self.rss_url)
                                except Exception:
                                    pass
                        else:
                            from ..adapters.rss_adapter import fetch_rss
                            try:
                                items = fetch_rss(self.rss_url, headers=self.headers, allow_robots=force_local)
                            except TypeError:
                                items = fetch_rss(self.rss_url, headers=self.headers)
                    except Exception:
                        from ..adapters.rss_adapter import fetch_rss
                        try:
                            items = fetch_rss(self.rss_url, headers=self.headers, allow_robots=force_local)
                        except TypeError:
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
                try:
                    if 'automaton-media.com' in (self.rss_url or ''):
                        from ..utils.automaton_url_parser import AutomatonUrlParser
                        parsed = AutomatonUrlParser.extract_post310463_articles(self.rss_url, headers=self.headers)
                        items = [
                            {'title': (p.get('title') or '').strip() or p.get('url'), 'link': p.get('url'), 'pubDate': '', 'description': ''}
                            for p in parsed
                        ]
                    elif 'gamespark.jp' in (self.rss_url or '') and '/category/' in (self.rss_url or ''):
                        from ..utils.gamespark_url_parser import GameSparkUrlParser
                        parsed = GameSparkUrlParser.extract_article_links(self.rss_url, headers=self.headers, include_alt=True)
                        items = [
                            {'title': (p.get('alt') or '').strip() or p.get('url'), 'link': p.get('url'), 'pubDate': '', 'description': ''}
                            for p in parsed
                        ]
                    else:
                        from ..adapters.rss_adapter import fetch_rss
                        items = fetch_rss(self.rss_url, headers=self.headers)
                except Exception:
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

