import sys
import threading
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWebEngineWidgets import QWebEngineView
from gamer.presenter.feed_presenter import FeedPresenter

BASE_URL = "https://www.4gamer.net/"
PC_RSS = "https://www.4gamer.net/rss/pc/pc_news.xml"
ONLINE_RSS = "https://www.4gamer.net/rss/all_onlinegame.xml"
RSS_URL = PC_RSS
# ジャンル名 -> RSS URL マップ
GENRES = {
    'オンライン': ONLINE_RSS,
    'PC': PC_RSS,
    'オンラインRPG': 'https://www.4gamer.net/rss/online/online_rpg.xml',
    'Xbox': 'https://www.4gamer.net/rss/xbox360/xbox360_news.xml',
    'PlayStation': 'https://www.4gamer.net/rss/ps3/ps3_news.xml',
    'PSP/Vita': 'https://www.4gamer.net/rss/psp/psp_news.xml',
    'Switch': 'https://www.4gamer.net/rss/nintendo_switch/nintendo_switch_news.xml',
    'Wii': 'https://www.4gamer.net/rss/wii/wii_news.xml',
    'DS': 'https://www.4gamer.net/rss/nds/nds_news.xml',
    'スマートフォン': 'https://www.4gamer.net/rss/smartphone/smartphone_index.xml',
    'ハードウェア': 'https://www.4gamer.net/rss/hardware/hw_news.xml',
    'アーケード': 'https://www.4gamer.net/rss/arcade/arcade_news.xml',
    'アナログ': 'https://www.4gamer.net/tags/TS/TS020/contents.xml',
    'VR': 'https://www.4gamer.net/rss/vr/vr_news.xml',
}
HEADERS = {"User-Agent": "4games-scraper/1.0 (+https://example.com)"}


# RSS は presenter に委譲します


class QtApp(QtWidgets.QMainWindow):
    status_message = QtCore.Signal(str, int)
    list_ready = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('4Gamer - QtWebEngine ビュー')
        self.resize(900, 640)
        self.rss_url = RSS_URL

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)

        # メニューバー: ジャンル選択（GENRES から自動生成）
        menubar = self.menuBar()
        genre_menu = menubar.addMenu('ジャンル')
        # QActionGroup が環境で利用できない場合もあるため、手動でチェック管理する
        self.genre_actions = {}
        for name, url in GENRES.items():
            # QAction may live in QtGui in some PySide6 builds
            try:
                act = QtWidgets.QAction(name, self)
            except Exception:
                act = QtGui.QAction(name, self)
            act.setCheckable(True)
            # 初期選択を反映
            if GENRES.get(name) == self.rss_url:
                act.setChecked(True)
            genre_menu.addAction(act)
            act.triggered.connect(lambda checked, n=name: self.change_genre(n))
            self.genre_actions[name] = act

        # 左: リスト
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setMaximumWidth(380)
        self.list_widget.itemActivated.connect(self.on_item_activated)
        # 選択が変わるたびに右側の Web 表示を更新
        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        h.addWidget(self.list_widget)

        # 右: QWebEngineView とそのラッパー
        raw_web = QWebEngineView()
        h.addWidget(raw_web, 1)
        try:
            from gamer.ui.webview import QtWebViewWrapper
            self.webview = QtWebViewWrapper(raw_web)
        except Exception:
            # fallback: expose raw view
            self.webview = None
        # keep reference for legacy code paths
        self.web = raw_web

        # ステータスバー
        self.status = self.statusBar()

        # シグナル接続
        self.status_message.connect(self.status.showMessage)
        self.list_ready.connect(self.populate_list)

        # Presenter を作成して RSS を読み込む（RssAdapter を依存注入）
        try:
            from gamer.adapters.rss_adapter import RssAdapter
            rss_adapter = RssAdapter()
        except Exception:
            rss_adapter = None
        self.presenter = FeedPresenter(self, self.rss_url, headers=HEADERS, rss_gateway=rss_adapter)
        # 非同期ロード
        self.presenter.load_feed()

    def load_url(self, url: str):
        try:
            if getattr(self, 'webview', None) is not None:
                self.webview.load(url)
            else:
                self.web.load(QtCore.QUrl(url))
        except Exception:
            pass

    # Implement ViewPort methods so presenter can call them directly
    def show_status(self, message: str, timeout_ms: int = 0) -> None:
        try:
            self.status_message.emit(message, timeout_ms)
        except Exception:
            pass

    def show_list(self, items) -> None:
        try:
            self.list_ready.emit(items)
        except Exception:
            pass

    @QtCore.Slot(object)
    def populate_list(self, items):
        self.items = items
        self.list_widget.clear()
        for it in items:
            title = it.get('title')
            pub = it.get('pubDate')
            txt = f"{pub} - {title}" if pub else title
            self.list_widget.addItem(txt)
        if items:
            # 最初の項目を自動で表示
            first = items[0]
            url = first.get('link')
            if url:
                self.web.load(QtCore.QUrl(url))

    def on_item_activated(self, item):
        idx = self.list_widget.row(item)
        self.presenter.select(idx)

    def on_row_changed(self, row: int):
        # 左リストの選択行が変わるたびに呼ばれる
        try:
            if row < 0:
                return
            if not hasattr(self, 'items') or row >= len(self.items):
                return
            self.presenter.select(row)
        except Exception:
            pass

    def change_genre(self, which: str):
        try:
            if which in GENRES:
                self.rss_url = GENRES[which]
                # チェック状態を更新
                for n, a in getattr(self, 'genre_actions', {}).items():
                    try:
                        a.setChecked(n == which)
                    except Exception:
                        pass
                self.status_message.emit(f'ジャンル: {which} に切替え', 2000)
            else:
                # unknown -> PC にフォールバック
                self.rss_url = PC_RSS
                self.status_message.emit('ジャンル: PC に切替え (既定)', 2000)
            # 再取得 via presenter
            self.presenter.rss_url = self.rss_url
            self.presenter.load_feed()
        except Exception:
            pass


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = QtApp()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
