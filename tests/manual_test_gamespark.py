from gamer.presenter.feed_presenter import FeedPresenter


class StubView:
    def __init__(self):
        self.items = None

    def show_status(self, msg, timeout):
        print('STATUS:', msg)

    def show_list(self, items):
        print('LIST COUNT:', len(items))
        for it in items:
            print(it.get('title'))
            print(' ', it.get('link'))


if __name__ == '__main__':
    view = StubView()
    url = 'https://www.gamespark.jp/category/pc/latest/?page=1'
    p = FeedPresenter(view=view, rss_url=url)
    items = p.load_feed_sync()
    print('Fetched', len(items), 'items')
