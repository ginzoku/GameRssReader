import sys

# Qt ランチャー: `qt_app.py` にデリゲートします
try:
    from PySide6 import QtCore  # presence check
except Exception as e:
    print("PySide6 が見つかりません。Qt を使うには PySide6 をインストールしてください。", e)
    print("Tk 実装のバックアップは backup/main_tk_backup.py にあります。")
    raise

try:
    import qt_app
except Exception as e:
    print("qt_app をインポートできませんでした:", e)
    raise


def main():
    qt_app.main()


if __name__ == '__main__':
    main()
