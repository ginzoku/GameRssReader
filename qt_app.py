import sys
import threading
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWebEngineWidgets import QWebEngineView

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


def fetch_rss(url=RSS_URL):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    items = []
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return items

    def find_local_text(elem, name):
        for child in elem:
            tag = child.tag
            if '}' in tag:
                local = tag.rsplit('}', 1)[1]
            else:
                local = tag
            if local == name:
                return child.text or ''
        return ''

    for elem in root.iter():
        tag = elem.tag
        local = tag.rsplit('}', 1)[1] if '}' in tag else tag
        if local.lower() == 'item':
            title = (find_local_text(elem, 'title') or '').strip() or "(タイトル取得できず)"
            link = (find_local_text(elem, 'link') or '').strip()
            pubdate = (find_local_text(elem, 'pubDate') or '').strip()
            desc_raw = (find_local_text(elem, 'description') or '').strip()
            desc = ''
            if desc_raw:
                desc = BeautifulSoup(desc_raw, 'html.parser').get_text(' ', strip=True)
            items.append({'title': title, 'link': link, 'pubDate': pubdate, 'description': desc})
    return items


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

        # 右: QWebEngineView
        self.web = QWebEngineView()
        h.addWidget(self.web, 1)

        # ステータスバー
        self.status = self.statusBar()

        # シグナル接続
        self.status_message.connect(self.status.showMessage)
        self.list_ready.connect(self.populate_list)

        # 背景でRSS取得
        threading.Thread(target=self.load_rss, daemon=True).start()

    def load_rss(self):
        try:
            # UI はシグナル経由で更新
            self.status_message.emit('RSS を取得中…', 0)
            items = fetch_rss(self.rss_url)
            self.list_ready.emit(items)
            self.status_message.emit('RSS を取得しました', 3000)
        except Exception as e:
            self.status_message.emit(f'RSS 取得エラー: {e}', 5000)

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
        if idx < 0 or idx >= len(self.items):
            return
        link = self.items[idx].get('link')
        if link:
            self.web.load(QtCore.QUrl(link))

    def on_row_changed(self, row: int):
        # 左リストの選択行が変わるたびに呼ばれる
        try:
            if row < 0:
                return
            if not hasattr(self, 'items') or row >= len(self.items):
                return
            link = self.items[row].get('link')
            if link:
                self.web.load(QtCore.QUrl(link))
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
            # 再取得
            threading.Thread(target=self.load_rss, daemon=True).start()
        except Exception:
            pass


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = QtApp()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
