import sys
import threading
from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWebEngineWidgets import QWebEngineView
from gamer.presenter.feed_presenter import FeedPresenter
from gamer.ui.webview import QtWebViewWrapper

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

# アーカイブ（キーワードベースの簡易フィルタ）
ARCHIVES = [
    'すべて表示',
    'ローグライト',
    'ローグライク',
]


class QtApp(QtWidgets.QMainWindow):
    status_message = QtCore.Signal(str, int)
    list_ready = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('4Gamer - QtWebEngine ビュー')
        self.resize(1000, 700)
        self.rss_url = RSS_URL

        # stylesheets (light + dark) and current theme helper
        self._light_stylesheet = '''
            QMainWindow { background: #f6f7fb; }
            QListWidget { background: white; border: 1px solid #e1e4ea; }
            QToolBar { background: transparent; spacing: 6px; }
            QMenuBar { background: transparent; }
            QStatusBar { background: transparent; }
        '''
        self._dark_stylesheet = '''
            QMainWindow { background: #0b0f14; color: #e6eef6; }
            QMenuBar { background: transparent; color: #e6eef6; }
            QMenu { background: #0b0f14; color: #e6eef6; border: 1px solid #162028; }
            QToolBar { background: transparent; spacing: 8px; padding: 6px; }
            QToolButton { color: #e6eef6; background: transparent; border-radius: 6px; padding: 6px; }
            QToolButton:hover { background: #16202a; }
            QListWidget { 
                background: #071018; 
                color: #e6eef6; 
                border: 1px solid #0f1a22; 
                padding: 6px; 
                border-radius: 8px;
            }
            QListWidget::item { 
                border-radius: 6px; 
                padding: 6px 4px; 
                margin: 2px 0; 
            }
            QListWidget::item:selected { 
                background: #133044; 
                color: #ffffff; 
            }
            QStatusBar { background: transparent; color: #9fb3c8; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 12px 0 12px 0; }
            QScrollBar::handle:vertical { background: #12303d; min-height: 20px; border-radius: 4px; }
            QSplitter::handle { background: transparent; }
        '''
        try:
            # default to dark theme
            self.setStyleSheet(self._dark_stylesheet)
        except Exception:
            pass

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)

        # メニューバー: ジャンル選択（GENRES から自動生成）
        menubar = self.menuBar()
        genre_menu = menubar.addMenu('ジャンル')
        # QActionGroup が環境で利用できない場合もあるため、手動でチェック管理する
        self.genre_actions = {}
        for name, url in GENRES.items():
            try:
                act = QtWidgets.QAction(name, self)
            except Exception:
                act = QtGui.QAction(name, self)
            act.setCheckable(True)
            if GENRES.get(name) == self.rss_url:
                act.setChecked(True)
            genre_menu.addAction(act)
            act.triggered.connect(lambda checked, n=name: self.change_genre(n))
            self.genre_actions[name] = act

        # アーカイブメニュー（キーワードで現在のリストをフィルタ）
        archive_menu = menubar.addMenu('アーカイブ')
        self.archive_actions = {}
        for key in ARCHIVES:
            try:
                a = QtWidgets.QAction(key, self)
            except Exception:
                a = QtGui.QAction(key, self)
            archive_menu.addAction(a)
            a.triggered.connect(lambda checked, k=key: self.change_archive(k))
            self.archive_actions[key] = a

        # 左: リスト
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setMaximumWidth(380)
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setSpacing(2)
        self.list_widget.itemActivated.connect(self.on_item_activated)
        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        # use custom delegate to draw wrapped, bold, white titles and control height
        try:
            class ArticleDelegate(QtWidgets.QStyledItemDelegate):
                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.padding = 8
                    self._font = QtGui.QFont()
                    self._font.setBold(True)
                    self._font.setPointSize(12)

                def paint(self, painter, option, index):
                    painter.save()
                    text = index.data(QtCore.Qt.DisplayRole) or ''
                    # background for selection
                    if option.state & QtWidgets.QStyle.State_Selected:
                        painter.fillRect(option.rect, QtGui.QColor('#133044'))
                        pen_color = QtGui.QColor('#ffffff')
                    else:
                        pen_color = QtGui.QColor('#e6eef6')
                    painter.setPen(pen_color)
                    painter.setFont(self._font)
                    doc = QtGui.QTextDocument()
                    to = doc.defaultTextOption()
                    to.setWrapMode(QtGui.QTextOption.WordWrap)
                    doc.setDefaultTextOption(to)
                    doc.setDefaultFont(self._font)
                    doc.setPlainText(text)
                    doc.setTextWidth(max(50, option.rect.width() - self.padding * 2))
                    painter.translate(option.rect.left() + self.padding, option.rect.top() + self.padding)
                    doc.drawContents(painter)
                    painter.restore()

                def sizeHint(self, option, index):
                    text = index.data(QtCore.Qt.DisplayRole) or ''
                    doc = QtGui.QTextDocument()
                    doc.setDefaultFont(self._font)
                    doc.setPlainText(text)
                    parent = self.parent()
                    width = 300
                    try:
                        if parent is not None:
                            width = max(80, parent.viewport().width() - self.padding * 2)
                    except Exception:
                        pass
                    doc.setTextWidth(width)
                    sz = doc.size().toSize()
                    sz.setHeight(sz.height() + self.padding * 2)
                    return sz

            self.list_widget.setItemDelegate(ArticleDelegate(self.list_widget))
        except Exception:
            pass

        # 右: QWebEngineView とそのラッパー
        raw_web = QWebEngineView()
        # use a splitter for modern resizable panes
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.list_widget)
        splitter.addWidget(raw_web)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 700])

        # wrap raw webview so wrapper behaviors (e.g. horizontal centering)
        # are actually used by the presenter/view methods
        try:
            self.webview = QtWebViewWrapper(raw_web)
        except Exception:
            # fallback to raw view if wrapper import/creation fails
            self.webview = raw_web

        # add splitter to central layout
        try:
            h.addWidget(splitter)
        except Exception:
            central.layout().addWidget(splitter)

        # status bar + signal hookup
        try:
            self._status_bar = QtWidgets.QStatusBar()
            self.setStatusBar(self._status_bar)
            try:
                # connect internal signal to status bar
                self.status_message.connect(lambda msg, t=0: self._status_bar.showMessage(msg, t))
            except Exception:
                pass
        except Exception:
            pass

        # initialize presenter and connect list-ready signal
        try:
            self.presenter = FeedPresenter(view=self, rss_url=self.rss_url)
            try:
                self.list_ready.connect(self.populate_list)
            except Exception:
                pass
            # start initial load
            try:
                self.presenter.load_feed()
            except Exception:
                pass
        except Exception:
            pass

    

    # Implement ViewPort methods so presenter can call them directly
    def load_url(self, url: str) -> None:
        try:
            # prefer wrapper interface which accepts a string URL
            try:
                self.webview.load(str(url))
                return
            except Exception:
                pass
            # fallback: try QWebEngineView.load with QUrl
            try:
                q = url if isinstance(url, QtCore.QUrl) else QtCore.QUrl(str(url))
                raw = getattr(self, 'webview', None) or getattr(self, 'web', None)
                if raw is not None:
                    # if raw is a wrapper, it may not accept QUrl; try .view.load
                    if hasattr(raw, 'view'):
                        raw.view.load(q)
                    else:
                        raw.load(q)
            except Exception:
                pass
        except Exception:
            pass
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
        # apply pending archive filter if any
        if getattr(self, '_pending_archive', None):
            items = self._apply_archive_filter(self._pending_archive, items)
            # clear pending
            self._pending_archive = None
        for it in items:
            title = it.get('title')
            pub = it.get('pubDate')
            txt = f"{pub} - {title}" if pub else title
            # use a QLabel inside the QListWidget so long titles wrap inside the list width
            item = QtWidgets.QListWidgetItem()
            label = QtWidgets.QLabel(txt)
            label.setWordWrap(True)
            # use contents margins for reliable spacing on all platforms
            try:
                # give extra bottom margin to avoid clipping of last line
                label.setContentsMargins(4, 4, 4, 8)
            except Exception:
                try:
                    label.setMargin(6)
                except Exception:
                    pass
            try:
                label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
            except Exception:
                pass
            label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            # let clicks pass through to QListWidget so item selection still works
            try:
                label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            except Exception:
                pass
            # make list text white and bold for better contrast in dark theme
            try:
                label.setStyleSheet('color: #ffffff; font-weight: 600; font-size: 13px;')
            except Exception:
                try:
                    f = label.font()
                    f.setBold(True)
                    f.setPointSize(12)
                    label.setFont(f)
                except Exception:
                    pass
            try:
                preferred = self.list_widget.maximumWidth() or self.list_widget.width() or 360
                label.setFixedWidth(max(120, preferred - 24))
            except Exception:
                pass
            label.adjustSize()
            try:
                sz = label.sizeHint()
                # add small vertical padding to avoid clipping of last line
                try:
                    sz.setHeight(sz.height() + 2)
                except Exception:
                    pass
                item.setSizeHint(sz)
            except Exception:
                item.setSizeHint(label.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, label)
        # try to process pending events so layout/viewport sizes are up-to-date,
        # then update item widths; fallback to scheduling if immediate update fails
        try:
            try:
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass
            self._update_list_item_widths()
        except Exception:
            try:
                QtCore.QTimer.singleShot(0, self._update_list_item_widths)
            except Exception:
                pass

    def resizeEvent(self, event):
        try:
            super().resizeEvent(event)
        except Exception:
            pass
        try:
            self._update_list_item_widths()
        except Exception:
            pass

    def _update_list_item_widths(self):
        vw = 0
        try:
            vw = self.list_widget.viewport().width()
        except Exception:
            return
        target_width = max(80, vw - 24)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget is None:
                continue
            try:
                widget.setFixedWidth(target_width)
                # force layout recalculation on the label
                try:
                    widget.adjustSize()
                except Exception:
                    pass
                sz = widget.sizeHint()
                # add larger vertical padding to ensure no clipping occurs
                try:
                    sz.setHeight(sz.height() + 8)
                except Exception:
                    pass
                item.setSizeHint(sz)
            except Exception:
                pass
        try:
            self.list_widget.updateGeometries()
            self.list_widget.viewport().update()
        except Exception:
            pass

    def _open_in_external(self):
        try:
            row = self.list_widget.currentRow()
            if row < 0:
                return
            url = self.items[row].get('link')
            if not url:
                return
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
        except Exception:
            pass

    def _apply_theme(self, dark: bool):
        try:
            if dark:
                self.setStyleSheet(self._dark_stylesheet)
            else:
                self.setStyleSheet(self._light_stylesheet)
        except Exception:
            pass

    def on_item_activated(self, item):
        idx = self.list_widget.row(item)
        self.presenter.select(idx)

    def on_row_changed(self, row: int):
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
                for n, a in getattr(self, 'genre_actions', {}).items():
                    try:
                        a.setChecked(n == which)
                    except Exception:
                        pass
                self.status_message.emit(f'ジャンル: {which} に切替え', 2000)
            else:
                self.rss_url = PC_RSS
                self.status_message.emit('ジャンル: PC に切替え (既定)', 2000)
            self.presenter.rss_url = self.rss_url
            self.presenter.load_feed()
        except Exception:
            pass

    def change_archive(self, which: str):
        try:
            if which == 'すべて表示':
                if hasattr(self, 'items'):
                    self.populate_list(self.items)
                else:
                    self._pending_archive = None
                self.status_message.emit('アーカイブ: すべて表示', 2000)
                return
            if not hasattr(self, 'items'):
                self._pending_archive = which
                self.status_message.emit(f'アーカイブ: {which} を適用します (読み込み後)', 2000)
                self.presenter.load_feed()
                return
            filtered = self._apply_archive_filter(which, self.items)
            self.populate_list(filtered)
            self.status_message.emit(f'アーカイブ: {which} を適用しました', 2000)
        except Exception:
            pass

    def _apply_archive_filter(self, keyword: str, items):
        if not keyword:
            return items
        out = []
        for it in items:
            title = (it.get('title') or '').lower()
            desc = (it.get('description') or '')
            text = f"{title} {desc}".lower()
            if keyword.lower() in text:
                out.append(it)
        return out


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = QtApp()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
