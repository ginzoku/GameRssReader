# 4Games.net 記事ビューア

この小さなアプリは `4games.net` の適当な記事を1つ取得して、ウィンドウ内にタイトルと本文の序盤を表示します。

必要条件
- Python 3.8+（Windowsで確認済み）

セットアップと実行（PowerShell の例）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

使い方
- 起動すると自動で適当な記事を取得して表示します。
- `記事を取得` ボタンで別の記事に切り替えできます。

注意
- ウェブスクレイピングのため、サイトの利用規約や robots.txt を確認してから利用してください。
- 著作権のある本文を公開する用途には注意してください。
