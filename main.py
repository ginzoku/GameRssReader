import threading
import random
import urllib.parse
import textwrap
import tkinter as tk
from tkinter import scrolledtext

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import webbrowser
import subprocess
import sys
try:
    from cefpython3 import cefpython as cef
    CEF_AVAILABLE = True
except Exception as e:
    print("CEF import failed:", e)
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

from gamer.ui.tk_app import App


def _cef_loop(root):
    cef.MessageLoopWork()
    root.after(10, lambda: _cef_loop(root))


def main():
    # Initialize CEF
    cef_settings = {}
    global CEF_AVAILABLE
    if CEF_AVAILABLE and cef is not None:
        try:
            cef.Initialize(settings=cef_settings)
        except Exception as e:
            # CEF の初期化に失敗したら代替動作へフォールバック
            print("CEF initialize failed:", e)
            CEF_AVAILABLE = False
    root = tk.Tk()
    app = App(root)
    # Start periodic CEF message loop integration
    if CEF_AVAILABLE:
        root.after(10, lambda: _cef_loop(root))

    def on_close():
        try:
            if CEF_AVAILABLE:
                cef.Shutdown()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
