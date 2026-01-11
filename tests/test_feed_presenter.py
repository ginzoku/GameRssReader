import unittest

from gamer.presenter.feed_presenter import FeedPresenter
from gamer.ports.view import ViewPort
from gamer.ports.rss_gateway import RssGateway


class StubView(ViewPort):
    def __init__(self):
        self.status_calls = []
        self.list_calls = []
        self.loaded_urls = []
        self.items = None

    def show_status(self, message: str, timeout_ms: int = 0) -> None:
        self.status_calls.append((message, timeout_ms))

    def show_list(self, items):
        self.list_calls.append(items)
        self.items = items

    def load_url(self, url: str) -> None:
        self.loaded_urls.append(url)


class StubRssGateway(RssGateway):
    def __init__(self, items):
        self._items = items

    def fetch(self, url: str, headers=None):
        return self._items


class FeedPresenterTest(unittest.TestCase):
    def test_load_feed_sync_calls_view(self):
        items = [{"title": "t", "link": "http://example/1"}]
        view = StubView()
        gateway = StubRssGateway(items)
        p = FeedPresenter(view, rss_url="http://rss", rss_gateway=gateway)

        result = p.load_feed_sync()
        self.assertEqual(result, items)
        self.assertEqual(len(view.list_calls), 1)
        self.assertIs(view.items, items)

    def test_select_loads_url(self):
        items = [{"title": "t", "link": "http://example/1"}]
        view = StubView()
        view.items = items
        p = FeedPresenter(view, rss_url="http://rss", rss_gateway=StubRssGateway(items))

        p.select(0)
        self.assertEqual(view.loaded_urls, ["http://example/1"])


if __name__ == "__main__":
    unittest.main()
