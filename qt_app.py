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

# サイトごとのジャンルマップ
SITES = {
    '4Gamer': {
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
    },
    'GameSpark': {
        '特集': 'https://www.gamespark.jp/category/featured/latest/?page=1',
        'PCゲーム': 'https://www.gamespark.jp/category/pc/latest/?page=1',
        '家庭用ゲーム': 'https://www.gamespark.jp/category/console/latest/?page=1',
        'セール・無料': 'https://www.gamespark.jp/category/news/sale/latest/?page=1',
    },
    'Automaton': {
        'PCゲーム': 'https://automaton-media.com/pc-steam-epic-games-store-gog/?query-19d0b21f=1',
    }
}

# デフォルトサイト
DEFAULT_SITE = '4Gamer'
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
        # paging settings
        self.page_size = 20
        self.current_page = 0

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
        # remove outer margins so panes align to window edges
        try:
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(0)
        except Exception:
            pass

        # 左側: サイト一覧をツリーで表示（クリックで展開、子要素クリックでジャンル選択）
        try:
            self.current_site = DEFAULT_SITE
            tree = QtWidgets.QTreeWidget()
            tree.setHeaderHidden(True)
            tree.setRootIsDecorated(False)
            # enable animated expand/collapse (slide-like expansion)
            try:
                tree.setAnimated(True)
            except Exception:
                pass

            # build tree: top-level = site, children = genres
            for site, genres in SITES.items():
                try:
                    top = QtWidgets.QTreeWidgetItem([site])
                    for name in genres.keys():
                        child = QtWidgets.QTreeWidgetItem([name])
                        top.addChild(child)
                    tree.addTopLevelItem(top)
                except Exception:
                    pass

            # collapse all initially
            try:
                for i in range(tree.topLevelItemCount()):
                    tree.topLevelItem(i).setExpanded(False)
            except Exception:
                pass

            def _on_item_clicked(item, col):
                try:
                    # top-level clicked -> toggle expand/collapse
                    if item.childCount() > 0:
                        item.setExpanded(not item.isExpanded())
                        return
                    # child clicked -> select genre
                    parent = item.parent()
                    if parent is None:
                        return
                    site = str(parent.text(0))
                    genre = str(item.text(0))
                    self.current_site = site
                    self.change_genre(genre)
                except Exception:
                    pass

            tree.itemClicked.connect(_on_item_clicked)

            # compute reasonable width from content and lock it (fixed)
            try:
                fm = tree.fontMetrics()
                maxw = 0
                for site, genres in SITES.items():
                    try:
                        w = fm.horizontalAdvance(str(site))
                        if w > maxw:
                            maxw = w
                    except Exception:
                        pass
                    for name in genres.keys():
                        try:
                            w = fm.horizontalAdvance(str(name))
                            if w > maxw:
                                maxw = w
                        except Exception:
                            pass
                padding = 48
                target = max(120, maxw + padding)
                # fix width so splitter can't resize it
                tree.setFixedWidth(target)
                tree.setMinimumWidth(target)
                tree.setMaximumWidth(target)
            except Exception:
                pass

            # style: match article list colors (dark theme)
            try:
                tree.setStyleSheet('''
                    QTreeWidget { background: #071018; color: #e6eef6; border: 1px solid #0f1a22; padding:6px; border-radius:8px; }
                    QTreeWidget::item { padding:4px 6px; }
                    QTreeWidget::item:selected { background: #133044; color: #ffffff; }
                ''')
            except Exception:
                pass

            self.left_panel = tree
            self.site_tree = tree
        except Exception:
            self.left_panel = None

        # 左: リスト
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setMaximumWidth(380)
        try:
            # remove inner margins/padding so items sit flush to the left edge
            self.list_widget.setContentsMargins(0, 0, 0, 0)
            self.list_widget.setStyleSheet("QListWidget{ padding: 2px; margin:0; }")
        except Exception:
            pass
        # allow per-item heights provided by the delegate/sizeHint
        self.list_widget.setUniformItemSizes(False)
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

                        # スタイルオプションを初期化（背景・選択状態などを正しく扱う）
                        style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
                        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)  # 背景・選択ハイライトを描画

                        text = index.data(QtCore.Qt.DisplayRole) or ''

                        if not text:
                            painter.restore()
                            return

                        # テキスト領域を padding 分縮小
                        text_rect = option.rect.adjusted(
                            self.padding, self.padding,
                            -self.padding, -self.padding
                        )

                        if text_rect.isEmpty():
                            painter.restore()
                            return

                        # QTextDocument 作成
                        doc = QtGui.QTextDocument()
                        doc.setDefaultFont(self._font)

                        option_text = QtGui.QTextOption()
                        option_text.setWrapMode(QtGui.QTextOption.WordWrap)
                        # option_text.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)  # 必要なら
                        doc.setDefaultTextOption(option_text)

                        doc.setPlainText(text)
                        doc.setTextWidth(max(
                                50, option.rect.width() - self.padding * 2
                            )
                        )


                        # ここが重要！ PaintContext を使って色とクリッピングを正しく制御
                        # あとListWidgetItemのSetForeGround()も効かない(そもそも今paint()をオーバーライドしてるから無視される)
                        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

                        # 選択状態か通常かで色を決める
                        if option.state & QtWidgets.QStyle.State_Selected:
                            painter.fillRect(option.rect, QtGui.QColor('#133044'))
                            ctx.palette.setColor(QtGui.QPalette.Text, QtGui.QColor('#ffffff'))
                            ctx.palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor('#ffffff'))
                        else:
                            ctx.palette.setColor(QtGui.QPalette.Text, QtGui.QColor('#ffffff'))

                        # クリッピングを設定（アイテム矩形内に収める）
                        ctx.clip = QtCore.QRectF(0, 0, text_rect.width(), text_rect.height())

                        # translate で移動してから描画
                        painter.translate(
                            option.rect.left() + self.padding,
                            option.rect.top() + self.padding
                        )

                        # drawContents() ではなく documentLayout().draw を使う（これが安定）
                        # PaintContext.paletteだけ確認してる作りっぽいのでsetPen()も無意味
                        # なのでctx.paletteで色を指定してそれを使用する以下の方法が必須
                        doc.documentLayout().draw(painter, ctx)

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

        # wrap list_widget in a container to add pager controls beneath
        try:
            self.list_container = QtWidgets.QWidget()
            list_layout = QtWidgets.QVBoxLayout(self.list_container)
            list_layout.setContentsMargins(0, 0, 0, 0)
            list_layout.setSpacing(4)
            list_layout.addWidget(self.list_widget)

            pager = QtWidgets.QWidget()
            pager_layout = QtWidgets.QHBoxLayout(pager)
            pager_layout.setContentsMargins(6, 4, 6, 4)
            pager_layout.setSpacing(6)
            try:
                # use QLabel with links (text-only look) for Prev/Next
                self.prev_label = QtWidgets.QLabel()
                self.page_label = QtWidgets.QLabel('Page 1/1')
                self.next_label = QtWidgets.QLabel()
                # right-align pager: add stretch first then widgets
                pager_layout.addStretch()
                pager_layout.addWidget(self.prev_label)
                pager_layout.addWidget(self.page_label)
                pager_layout.addWidget(self.next_label)
                list_layout.addWidget(pager)
                try:
                    # make link-like appearance
                    for lbl in (self.prev_label, self.next_label):
                        lbl.setTextFormat(QtCore.Qt.RichText)
                        lbl.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
                        lbl.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                        lbl.setStyleSheet('color: #9fb3c8; background: transparent;')
                    self.prev_label.linkActivated.connect(lambda _: self._on_prev())
                    self.next_label.linkActivated.connect(lambda _: self._on_next())
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            self.list_container = self.list_widget

        # 右: QWebEngineView とそのラッパー
        raw_web = QWebEngineView()
        # wrap the raw webview in a container so overlay widgets can be parented reliably
        web_container = QtWidgets.QWidget()
        web_layout = QtWidgets.QVBoxLayout(web_container)
        web_layout.setContentsMargins(0, 0, 0, 0)
        web_layout.setSpacing(0)
        web_layout.addWidget(raw_web)

        # use a splitter for modern resizable panes
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        try:
            splitter.setHandleWidth(6)
        except Exception:
            pass
        # insert left panel (tree), article list, and web view
        try:
            if getattr(self, 'left_panel', None) is not None:
                splitter.addWidget(self.left_panel)
        except Exception:
            pass
        # add the list container (which includes pager) instead of raw list_widget
        try:
            splitter.addWidget(getattr(self, 'list_container', self.list_widget))
        except Exception:
            splitter.addWidget(self.list_widget)
        splitter.addWidget(web_container)
        # make columns: left_panel, article, web — give remaining space to web view
        try:
            try:
                splitter.setStretchFactor(0, 0)
                splitter.setStretchFactor(1, 0)
                splitter.setStretchFactor(2, 1)
            except Exception:
                pass
            # prevent left panel from being collapsible / resizable
            try:
                splitter.setCollapsible(0, False)
            except Exception:
                pass
            try:
                left_w = self.left_panel.width() if getattr(self, 'left_panel', None) is not None else 140
            except Exception:
                left_w = 140
            try:
                list_w = min(380, max(200, int(self.width() * 0.3)))
            except Exception:
                list_w = 300
            try:
                web_w = max(200, self.width() - left_w - list_w)
            except Exception:
                web_w = 700
            splitter.setSizes([left_w, list_w, web_w])
        except Exception:
            try:
                splitter.setStretchFactor(1, 1)
                splitter.setSizes([300, 700])
            except Exception:
                pass

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
                # also connect to handler to detect robots block messages and prompt override
                try:
                    self.status_message.connect(self._on_status_message)
                except Exception:
                    pass
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
        # store full items and reset to first page
        self.full_items = items or []
        # keep legacy `items` attribute for presenter compatibility
        try:
            self.items = self.full_items
        except Exception:
            pass
        # apply pending archive filter if any
        if getattr(self, '_pending_archive', None):
            self.full_items = self._apply_archive_filter(self._pending_archive, self.full_items)
            self._pending_archive = None
        try:
            self.current_page = 0
        except Exception:
            pass
        # render current page
        try:
            self._render_page()
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

    def _render_page(self):
        try:
            items = getattr(self, 'full_items', []) or []
            total = len(items)
            if total == 0:
                self.list_widget.clear()
                try:
                    self.page_label.setText('Page 0/0')
                except Exception:
                    pass
                return

            start = self.current_page * self.page_size
            end = start + self.page_size
            page_items = items[start:end]

            self.list_widget.clear()
            for it in page_items:
                try:
                    title = it.get('title')
                    pub = it.get('pubDate')
                    txt = f"{pub} - {title}" if pub else title
                    item = QtWidgets.QListWidgetItem(str(txt or ''))
                    try:
                        fnt = item.font()
                        fnt.setBold(True)
                        fnt.setPointSize(12)
                        item.setFont(fnt)
                    except Exception:
                        pass
                    try:
                        item.setForeground(QtGui.QColor('#ffffff'))
                    except Exception:
                        pass
                    self.list_widget.addItem(item)
                except Exception:
                    pass

            # update page label and controls
            try:
                total_pages = max(1, (total + self.page_size - 1) // self.page_size)
                self.page_label.setText(f'Page {self.current_page+1}/{total_pages}')
                self._update_page_controls(total, total_pages)
            except Exception:
                pass

            try:
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass
            try:
                self._update_list_item_widths()
            except Exception:
                pass
        except Exception:
            pass

    def _on_prev(self):
        try:
            if self.current_page > 0:
                self.current_page -= 1
                self._render_page()
        except Exception:
            pass

    def _on_next(self):
        try:
            items = getattr(self, 'full_items', []) or []
            total = len(items)
            total_pages = max(1, (total + self.page_size - 1) // self.page_size)
            if self.current_page + 1 < total_pages:
                self.current_page += 1
                self._render_page()
        except Exception:
            pass

    def _update_page_controls(self, total, total_pages):
        try:
            if total <= 0:
                try:
                    try:
                        # show plain text when disabled
                        self.prev_label.setText('Prev')
                        self.next_label.setText('Next')
                        self.prev_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
                        self.next_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
                    except Exception:
                        pass
                except Exception:
                    pass
                return
            try:
                # update prev/next as links when enabled, plain text when disabled
                if self.current_page > 0:
                    try:
                        self.prev_label.setText("<a href='prev'>Prev</a>")
                        self.prev_label.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                    except Exception:
                        pass
                else:
                    try:
                        self.prev_label.setText('Prev')
                        self.prev_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
                    except Exception:
                        pass

                if self.current_page + 1 < total_pages:
                    try:
                        self.next_label.setText("<a href='next'>Next</a>")
                        self.next_label.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                    except Exception:
                        pass
                else:
                    try:
                        self.next_label.setText('Next')
                        self.next_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def _open_in_external(self):
        try:
            row = self.list_widget.currentRow()
            if row < 0:
                return
            # convert page-local row to global index
            global_idx = getattr(self, 'current_page', 0) * getattr(self, 'page_size', 20) + row
            items = getattr(self, 'full_items', None) or getattr(self, 'items', None) or []
            url = None
            try:
                url = items[global_idx].get('link')
            except Exception:
                url = None
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
        try:
            idx = self.list_widget.row(item)
            global_idx = getattr(self, 'current_page', 0) * getattr(self, 'page_size', 20) + idx
            self.presenter.select(global_idx)
        except Exception:
            pass

    def on_row_changed(self, row: int):
        try:
            if row < 0:
                return
            # convert page-local row to global index
            items = getattr(self, 'full_items', None) or getattr(self, 'items', None)
            if items is None:
                return
            global_idx = getattr(self, 'current_page', 0) * getattr(self, 'page_size', 20) + row
            if global_idx >= len(items):
                return
            self.presenter.select(global_idx)
        except Exception:
            pass

    def change_genre(self, which: str):
        try:
            site_map = SITES.get(getattr(self, 'current_site', DEFAULT_SITE), {})
            if which in site_map:
                self.rss_url = site_map[which]
                # update selection in genre_list if present
                try:
                    if getattr(self, 'genre_list', None) is not None:
                        for i, n in enumerate(site_map.keys()):
                            try:
                                if n == which:
                                    self.genre_list.setCurrentRow(i)
                                    break
                            except Exception:
                                pass
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

    def _on_status_message(self, msg: str, timeout: int = 0):
        try:
            if not msg:
                return
            key = 'robots.txt により取得が拒否されました:'
            if msg.startswith(key):
                url = msg[len(key):].strip()
                try:
                    from PySide6.QtWidgets import QMessageBox
                    ret = QMessageBox.question(self, 'robots.txt によるブロック',
                                               f'robots.txt により次のページの取得が拒否されました:\n{url}\n\n取得を強制しますか？\n(サイトの利用規約に違反していないか確認してください)',
                                               QMessageBox.Yes | QMessageBox.No,
                                               QMessageBox.No)
                    if ret == QMessageBox.Yes:
                        try:
                            self.presenter.load_feed(force=True)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    # NOTE: site/genre row handlers removed — tabs+combo handle selection now

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
