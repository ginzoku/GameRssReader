from typing import Optional

from PySide6 import QtCore
from PySide6.QtCore import QUrl, QEvent, Qt
from PySide6.QtWidgets import QLabel, QPushButton, QWidget, QHBoxLayout
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineWidgets import QWebEngineView

from ..ports.webview import WebViewPort


class QtWebViewWrapper(WebViewPort):
    """Wrapper around QWebEngineView implementing WebViewPort."""

    def __init__(self, view: Optional[QWebEngineView] = None):
        if view is None:
            self.view = QWebEngineView()
        else:
            self.view = view
        # simple wrapper: allow optional automatic horizontal centering on load
        self._center_horizontal = True
        try:
            self.view.loadFinished.connect(self._on_load_finished)
        except Exception:
            pass
        # install an internal event filter to track resize/move events for positioning the bottom bar
        try:
            class _ViewEventFilter(QtCore.QObject):
                def __init__(self, wrapper):
                    super().__init__(wrapper)
                    self._wrapper = wrapper

                def eventFilter(self, obj, event):
                    try:
                        if event.type() in (QEvent.Resize, QEvent.Move):
                            # reposition when the view or its parent moves/resizes
                            try:
                                self._wrapper._position_bottom_bar()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    return False

            self._view_event_filter = _ViewEventFilter(self)
            try:
                self.view.installEventFilter(self._view_event_filter)
            except Exception:
                pass
        except Exception:
            pass

        # ensure empty state uses black background
        try:
            self.clear()
        except Exception:
            pass
        # create bottom URL bar (hidden when not available)
        try:
            self._create_bottom_bar()
        except Exception:
            pass
    def load(self, url: str) -> None:
        try:
            # disable automatic horizontal centering for GameSpark (their layout)
            try:
                u = str(url or '')
            except Exception:
                u = ''
            if 'gamespark.jp' in u:
                self._center_horizontal = False
            else:
                # preserve default unless explicitly disabled elsewhere
                self._center_horizontal = True
            # update URL label immediately
            try:
                if getattr(self, '_url_label', None) is not None:
                    self._url_label.setText(u)
                    try:
                        if getattr(self, '_bottom_bar', None) is not None:
                            self._bottom_bar.show()
                            self._position_bottom_bar()
                    except Exception:
                        pass
            except Exception:
                pass
            self.view.load(QtCore.QUrl(url))
        except Exception:
            # swallow to keep presenter resilient
            pass

    def set_html(self, html: str, base_url: str = "about:blank") -> None:
        try:
            page = self.view.page()
            page.setHtml(html, QtCore.QUrl(base_url))
        except Exception:
            pass

    def _on_load_finished(self, ok: bool):
        if not ok:
            return
        if not self._center_horizontal:
            return
        js = '''(function(){
            try{
                var w = window.innerWidth || document.documentElement.clientWidth;
                var sw = document.documentElement.scrollWidth || document.body.scrollWidth || 0;
                var target = Math.max(0, Math.floor((sw - w) / 2));
                window.scrollTo(target, 0);
            }catch(e){ /* ignore */ }
        })();'''
        try:
            page = self.view.page()
            page.runJavaScript(js)
        except Exception:
            pass

        # refresh displayed url to the page's canonical url
        try:
            if getattr(self, '_url_label', None) is not None:
                try:
                    page_url = self.view.page().url().toString()
                except Exception:
                    page_url = ''
                if page_url:
                    self._url_label.setText(page_url)
        except Exception:
            pass

    def clear(self) -> None:
        try:
            # show an explicit black page instead of default white about:blank
            html = '<!doctype html><html><head><meta charset="utf-8"></head>' \
                   '<body style="background:#000000;margin:0;height:100%;"></body></html>'
            page = self.view.page()
            # prefer setHtml so background is immediately black
            try:
                page.setHtml(html, QtCore.QUrl('about:blank'))
                return
            except Exception:
                pass
            # fallback to loading about:blank if setHtml not available
            self.view.load(QtCore.QUrl("about:blank"))
        except Exception:
            pass

    def set_center_horizontal(self, enable: bool) -> None:
        """Enable/disable automatic horizontal centering after page load."""
        self._center_horizontal = bool(enable)

    def _create_bottom_bar(self, height: int = 36):
        try:
            if getattr(self, '_bottom_bar', None) is not None:
                return
            # parent the bottom bar to the view's parent (e.g., the splitter pane)
            parent_widget = self.view.parent() or self.view
            bar = QWidget(parent_widget)
            bar.setObjectName('webview_bottom_bar')
            bar.setFixedHeight(height)
            bar.setStyleSheet('background: rgba(0,0,0,0.65); color: white;')

            layout = QHBoxLayout(bar)
            layout.setContentsMargins(8, 4, 8, 4)
            layout.setSpacing(8)

            url_label = QLabel('', bar)
            url_label.setStyleSheet('color: white;')
            url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(url_label, 1)

            btn = QPushButton('外部で開く', bar)
            btn.setToolTip('現在表示中のページを外部ブラウザで開く')
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet('background: rgba(255,255,255,0.1); color: white; border-radius:4px; padding:4px 8px;')
            btn.clicked.connect(self._open_in_external)
            layout.addWidget(btn, 0)

            bar.hide()
            bar.setLayout(layout)

            self._bottom_bar = bar
            self._url_label = url_label
            self._open_btn = btn
            # position initially
            self._position_bottom_bar()
            # also install event filter on parent to catch parent resizes
            try:
                parent_widget.installEventFilter(self._view_event_filter)
            except Exception:
                pass
        except Exception:
            pass

    def _position_bottom_bar(self, margin: int = 6):
        try:
            bar = getattr(self, '_bottom_bar', None)
            if not bar:
                return
            parent_widget = bar.parent() or self.view
            # compute view position relative to parent to position the bar correctly
            try:
                top_left = self.view.mapToParent(QtCore.QPoint(0, 0))
                vx = top_left.x()
                vy = top_left.y()
                vw = self.view.width()
                vh = self.view.height()
            except Exception:
                # fallback
                try:
                    geom = self.view.geometry()
                    vx = geom.x(); vy = geom.y(); vw = geom.width(); vh = geom.height()
                except Exception:
                    vx = 0; vy = 0; vw = self.view.width(); vh = self.view.height()
            bh = bar.height()
            x = vx
            y = vy + max(0, vh - bh - margin)
            bar.setGeometry(x, y, vw, bh)
            bar.raise_()
            # show if page has a URL
            try:
                cur = self.view.page().url().toString()
            except Exception:
                cur = ''
            if cur:
                bar.show()
                try:
                    self._url_label.setText(cur)
                except Exception:
                    pass
            else:
                bar.hide()
        except Exception:
            pass

    def _open_in_external(self):
        try:
            try:
                url = self.view.page().url().toString()
            except Exception:
                url = ''
            if not url:
                try:
                    url = self.view.url().toString()
                except Exception:
                    url = ''
            if url:
                QDesktopServices.openUrl(QUrl(url))
        except Exception:
            pass
