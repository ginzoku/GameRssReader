import threading
import random
import urllib.parse
import textwrap
import tkinter as tk
from tkinter import scrolledtext

import webbrowser
import subprocess
import sys
try:
    from cefpython3 import cefpython as cef
    CEF_AVAILABLE = True
except Exception:
    cef = None
    CEF_AVAILABLE = False
try:
    import webview
except Exception:
    webview = None

import ctypes
from ctypes import wintypes
import tempfile
import shutil
import os

from gamer.domain.usecases import prepare_feed_and_initial_article, get_full_article
from gamer.adapters.browser_adapter import default_browser_adapter
from gamer.presenter.feed_presenter import FeedPresenter


class App:
    def __init__(self, root):
        self.root = root
        root.title("4Games.net の記事表示")
        root.geometry("720x480")
        # 上部ボタン領域
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(fill=tk.X, padx=8, pady=6)

        self.fetch_btn = tk.Button(self.btn_frame, text="RSSを取得", command=self.async_fetch)
        self.fetch_btn.pack(side=tk.LEFT)

        self.status_label = tk.Label(self.btn_frame, text="準備完了")
        self.status_label.pack(side=tk.LEFT, padx=8)

        # メイン領域を左右に分割: 左にタイトル一覧、右に詳細
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # 左: タイトル一覧
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.listbox = tk.Listbox(self.left_frame, width=40)
        self.listbox.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        self.lb_scroll = tk.Scrollbar(self.left_frame, command=self.listbox.yview)
        self.lb_scroll.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.config(yscrollcommand=self.lb_scroll.set)

        # 右: 詳細表示 + ボタン
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 内部にCEFブラウザを埋め込むため、右枠は空のコンテナにする
        self.text = scrolledtext.ScrolledText(self.right_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.text.pack(fill=tk.BOTH, expand=True)

        self.open_btn = tk.Button(self.right_frame, text="記事をブラウザで開く (右枠表示)", command=self.open_selected)
        self.open_btn.pack(fill=tk.X, pady=(6,0))

        self.rss_items = []
        self.browser = None
        self.pw_window = None
        self.pw_thread = None
        self._pw_hwnd = None
        self.browser_adapter = default_browser_adapter
        # Presenter を作成して view を接続
        self.presenter = FeedPresenter(browser_adapter_instance=self.browser_adapter)
        self.presenter.attach_view(self)
        # CEF用の初期化は外側で行う。ここで右枠のリサイズハンドラを設定
        self.right_frame.bind('<Configure>', self.on_right_configure)
        # 初回ロード
        self.presenter.load_feed()

    def set_status(self, text):
        self.status_label.config(text=text)

    # Presenter が非同期で処理するため UI 側の fetch helper は不要

    def create_browser_embedded(self, url="about:blank"):
        # CEF browser を右枠内に埋め込む
        if not CEF_AVAILABLE:
            return
        if self.browser:
            try:
                self.browser.LoadUrl(url)
                return
            except Exception:
                pass
        # Ensure window IDs are created
        self.root.update_idletasks()
        hwnd = self.right_frame.winfo_id()
        width = max(1, self.right_frame.winfo_width())
        height = max(1, self.right_frame.winfo_height())
        window_info = cef.WindowInfo()
        try:
            window_info.SetAsChild(hwnd, [0, 0, width, height])
        except Exception:
            # fallback if signature differs
            window_info.SetAsChild(hwnd)
        self.browser = cef.CreateBrowserSync(window_info=window_info, url=url)

    # --- pywebview 子ウィンドウ化用ヘルパー (Windows) ---
    def _start_pywebview_thread(self, url):
        # create_window must be called from the GUI thread of pywebview
        try:
            # Create hidden window so we can parent it before showing
            # Use a unique user_data_dir per webview to avoid conflicts on cleanup
            self._pw_userdir = tempfile.mkdtemp(prefix='pywebview_')
            try:
                # pass user_data_dir if supported
                try:
                    self.pw_window = webview.create_window('EmbeddedView', url, hidden=True, user_data_dir=self._pw_userdir)
                except TypeError:
                    # older pywebview may not support hidden or user_data_dir params
                    try:
                        self.pw_window = webview.create_window('EmbeddedView', url, hidden=True)
                    except TypeError:
                        self.pw_window = webview.create_window('EmbeddedView', url)
            except Exception:
                # fallback to non-hidden creation
                self.pw_window = webview.create_window('EmbeddedView', url)
            webview.start()
        except Exception:
            self.pw_window = None

    def embed_pywebview_into_frame(self, url):
        # Try to start pywebview in a background thread and SetParent to right_frame
        if webview is None:
            return False
        # If already started, just load URL
        try:
            if self.pw_window:
                try:
                    self.pw_window.load_url(url)
                except Exception:
                    pass
                return True
        except Exception:
            pass

        # Start pywebview in a thread
        self.pw_thread = threading.Thread(target=self._start_pywebview_thread, args=(url,), daemon=True)
        self.pw_thread.start()

        # Poll for window handle
        HWND = None
        for _ in range(400):
            if self.pw_window is not None:
                hwnd = getattr(self.pw_window, '_hwnd', None)
                if hwnd:
                    HWND = hwnd
                    break
            # sometimes window may be created with attribute 'hwnd'
            if self.pw_window is not None:
                hwnd = getattr(self.pw_window, 'hwnd', None)
                if hwnd:
                    HWND = hwnd
                    break
            threading.Event().wait(0.05)

        if not HWND:
            # fallback: try to find window by title
            try:
                import time
                import win32gui
                for _ in range(50):
                    hwnd = win32gui.FindWindow(None, 'EmbeddedView')
                    if hwnd:
                        HWND = hwnd
                        break
                    time.sleep(0.05)
            except Exception:
                pass

        if not HWND:
            return False

        # Parent it to the right_frame
        try:
            parent_hwnd = self.right_frame.winfo_id()
            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_CHILD = 0x40000000
            WS_POPUP = 0x80000000
            SWP_NOZORDER = 0x0004
            SWP_SHOWWINDOW = 0x0040

            # Set parent
            user32.SetParent(HWND, parent_hwnd)

            # Adjust window style to child (so it moves with parent)
            try:
                SetWindowLongPtr = user32.SetWindowLongPtrW
                GetWindowLongPtr = user32.GetWindowLongPtrW
            except AttributeError:
                SetWindowLongPtr = user32.SetWindowLongW
                GetWindowLongPtr = user32.GetWindowLongW

            style = GetWindowLongPtr(HWND, GWL_STYLE)
            style = (style | WS_CHILD) & ~WS_POPUP
            SetWindowLongPtr(HWND, GWL_STYLE, style)

            # Position it
            w = max(1, self.right_frame.winfo_width())
            h = max(1, self.right_frame.winfo_height())
            user32.SetWindowPos(HWND, 0, 0, 0, w, h, SWP_NOZORDER | SWP_SHOWWINDOW)
            # Ensure the child is shown
            try:
                SW_SHOW = 5
                user32.ShowWindow(HWND, SW_SHOW)
            except Exception:
                pass
            # store handle for resize updates
            self._pw_hwnd = HWND
            return True
        except Exception:
            # cleanup userdir if created
            try:
                ud = getattr(self, '_pw_userdir', None)
                if ud and os.path.exists(ud):
                    shutil.rmtree(ud, ignore_errors=True)
            except Exception:
                pass
            return False

    def on_right_configure(self, event):
        # リサイズ時に CEF のウィンドウサイズを更新
        if CEF_AVAILABLE and self.browser:
            try:
                host = self.browser.GetHost()
                host.SetWindowBounds(0, 0, event.width, event.height)
            except Exception:
                pass
        # pywebview embedded: resize child window if present
        try:
            hwnd = getattr(self, '_pw_hwnd', None)
            if hwnd:
                user32 = ctypes.windll.user32
                SWP_NOZORDER = 0x0004
                SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(hwnd, 0, 0, 0, event.width, event.height, SWP_NOZORDER | SWP_SHOWWINDOW)
        except Exception:
            pass

    def do_fetch(self):
        try:
            # RSS一覧を取得して左側リストに反映
            self.set_status("RSS を取得中…")
            items, first = prepare_feed_and_initial_article()
            self.rss_items = items
            if items:
                # UI スレッドでリストを更新
                self.root.after(0, lambda: self.populate_list(items))
            if first:
                self.show_article(first.title, first.description, first.link)
                self.set_status(f"表示: {first.link}")
            else:
                raise RuntimeError("候補リンクが見つかりませんでした")
        except Exception as e:
            self.show_article("エラー", str(e), "")
            self.set_status("エラー発生")

    def show_article(self, title, snippet, url):
        display = f"{title}\n\n{snippet or ''}\n\n元URL: {url}"
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, display)
        self.text.config(state=tk.DISABLED)

    def populate_list(self, items):
        self.listbox.delete(0, tk.END)
        for it in items:
            title = getattr(it, 'title', '')
            pub = getattr(it, 'pubDate', None)
            display = f"{title}"
            if pub:
                display = f"{pub} - {title}"
            self.listbox.insert(tk.END, display)

    # Presenter と互換性のためのエイリアスメソッド
    def show_list(self, items):
        return self.populate_list(items)

    def on_select(self, event):
        sel = event.widget.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self.rss_items):
            return
        # Presenter に選択イベントを渡す
        self.presenter.select(idx)

    def open_selected(self):
        # 右枠で全文表示する（ブラウザを開かない）
        text = self.text.get("1.0", tk.END)
        marker = "元URL: "
        idx = text.find(marker)
        if idx == -1:
            return
        url = text[idx+len(marker):].strip()
        if url:
            # Presenter に処理を委譲
            try:
                # prefer in-app rendering first
                threading.Thread(target=self.display_full_article_in_app, args=(url,), daemon=True).start()
            except Exception:
                self.presenter.open_url(url)

    def display_full_article_in_app(self, url):
        """記事を取得して、Tk ウィジェットで枠風に表示する（外部レンダラ不要）。"""
        try:
            self.set_status("記事全文を取得中…")
            art = get_full_article(url)
            # UI スレッドで描画
            self.root.after(0, lambda: self.render_article_widgets(art.title, art.body, art.link))
            self.set_status(f"表示: {art.link}")
        except Exception as e:
            self.root.after(0, lambda: self.show_article("エラー", str(e), ""))
            self.set_status("エラー発生")

    def render_article_widgets(self, title, body, url):
        # 既存のテキストウィジェットを隠してフォーマット表示用ウィジェットを作成
        try:
            # Destroy previous article frame if exists
            if hasattr(self, 'article_frame') and self.article_frame:
                try:
                    self.article_frame.destroy()
                except Exception:
                    pass
            # Hide plain text widget
            try:
                self.text.pack_forget()
            except Exception:
                pass

            self.article_frame = tk.Frame(self.right_frame)
            self.article_frame.pack(fill=tk.BOTH, expand=True)

            # Title
            title_lbl = tk.Label(self.article_frame, text=title, font=(None, 14, 'bold'), wraplength=600, justify=tk.LEFT)
            title_lbl.pack(anchor=tk.W, padx=8, pady=(8,4))

            # Scrollable body
            body_scroller = scrolledtext.ScrolledText(self.article_frame, wrap=tk.WORD, state=tk.NORMAL)
            body_scroller.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
            body_scroller.insert(tk.END, body)
            body_scroller.config(state=tk.DISABLED)

            # ボタン群
            btn_frame = tk.Frame(self.article_frame)
            btn_frame.pack(fill=tk.X, padx=8, pady=(4,8))
            open_ext = tk.Button(btn_frame, text="外部で開く", command=lambda: webbrowser.open(url))
            open_ext.pack(side=tk.LEFT)
            restore_btn = tk.Button(btn_frame, text="プレーン表示に戻す", command=self.restore_plain_text_view)
            restore_btn.pack(side=tk.LEFT, padx=(6,0))
        except Exception as e:
            # フォールバック: 既存の show_article を使う
            self.show_article(title, body, url)

    def restore_plain_text_view(self):
        # 枠風表示を閉じて元のシンプルなテキスト表示に戻す
        try:
            if hasattr(self, 'article_frame') and self.article_frame:
                try:
                    self.article_frame.destroy()
                except Exception:
                    pass
            # show_article の内容を再表示（既に最後に表示していたテキストを復元）
            # 簡易的に現在のテキストは空にしておく
            self.text.config(state=tk.NORMAL)
            self.text.delete('1.0', tk.END)
            self.text.insert(tk.END, "記事を選択してください。")
            self.text.config(state=tk.DISABLED)
            self.text.pack(fill=tk.BOTH, expand=True)
        except Exception:
            pass

    def display_full_article_from_link(self, url):
        try:
            # このメソッドは互換性のため残すが、Presenter を使うのが推奨
            self.set_status("記事全文を取得中…")
            art = get_full_article(url)
            # UIスレッドで表示
            self.root.after(0, lambda: self.show_article(art.title, art.body, art.link))
            self.set_status(f"表示: {art.link}")
            # 埋め込みは Presenter/Adapter 経由で行う
            try:
                self.root.after(0, lambda: self.presenter.open_url(url))
            except Exception:
                pass
        except Exception as e:
            self.root.after(0, lambda: self.show_article("エラー", str(e), ""))
            self.set_status("エラー発生")
