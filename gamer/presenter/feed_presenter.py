import threading
from typing import Optional, Any

from gamer.domain import usecases
from gamer.adapters import browser_adapter
from gamer.domain.entities import Article


class FeedPresenter:
    """薄い Presenter: UI イベントを受けユースケースとアダプタを呼ぶ。

    View には少なくとも次のメソッドが必要:
    - show_list(items)
    - show_article(title, body_or_snippet, url)
    - set_status(text)
    """

    def __init__(self, view: Optional[Any] = None, browser_adapter_instance=None):
        self.view = view
        self.browser_adapter = browser_adapter_instance or browser_adapter.default_browser_adapter

    def attach_view(self, view: Any):
        self.view = view

    def load_feed(self):
        t = threading.Thread(target=self._load_feed, daemon=True)
        t.start()

    def _load_feed(self):
        if not self.view:
            return
        try:
            self.view.set_status("RSS を取得中…")
            items, first = usecases.prepare_feed_and_initial_article()
            # ビューに一覧を渡す
            try:
                self.view.show_list(items)
            except Exception:
                # 互換性のため populate_list も試す
                if hasattr(self.view, 'populate_list'):
                    self.view.populate_list(items)
            if first:
                self.view.show_article(first.title, first.description, first.link)
                self.view.set_status(f"表示: {first.link}")
            else:
                self.view.set_status("候補リンクが見つかりませんでした")
        except Exception as e:
            self.view.show_article("エラー", str(e), "")
            self.view.set_status("エラー発生")

    def select(self, index: int):
        t = threading.Thread(target=self._select, args=(index,), daemon=True)
        t.start()

    def _select(self, index: int):
        if not self.view:
            return
        try:
            if not hasattr(self.view, 'rss_items'):
                return
            if index < 0 or index >= len(self.view.rss_items):
                return
            item = self.view.rss_items[index]
            url = getattr(item, 'link', None)
            if not url:
                return
            self.view.set_status("記事全文を取得中…")
            art = usecases.get_full_article(url)
            self.view.show_article(art.title, art.body or art.description, art.link)
            self.view.set_status(f"表示: {art.link}")
        except Exception as e:
            self.view.show_article("エラー", str(e), "")
            self.view.set_status("エラー発生")

    def open_url(self, url: str):
        try:
            # delegate to adapter; adapter may embed or open external
            return self.browser_adapter.embed_or_open(self.view, url)
        except Exception:
            try:
                self.browser_adapter.open_external(url)
            except Exception:
                pass
            return False
