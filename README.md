# 4Gamer 記事ビューワ（GameRssReader）

シンプルなデスクトップ向け RSS/記事ビューワです。4Gamer の RSS を取得して一覧表示し、選択した記事を組み込みブラウザまたは外部ブラウザで表示します。

主な機能
- RSS フィードの取得と一覧表示（複数ジャンルに対応）
- 記事本文の要約（サニタイズ済みテキスト）表示
- 組み込みブラウザ表示（`cefpython3` または `pywebview` を利用、未インストール時はフォールバック）
 - 組み込みブラウザ表示（最終レンダラ: Qt の `QWebEngineView` を使用。CEF/pywebview は非推奨）
- Qt ベースの別アプリケーション（`qt_app.py`）を含む

対応プラットフォーム
- Windows（開発・動作確認済み）

要件
- Python 3.8 以上
- 必須パッケージ: `requests`, `beautifulsoup4`
- オプション（機能に応じて）: `cefpython3`（埋め込みCEF）、`pywebview`（埋め込みWebViewの代替）、`PySide6`（`qt_app.py` を実行する場合）
 - オプション（機能に応じて）: `PySide6`（`qt_app.py` を実行する場合）。`cefpython3` や `pywebview` は現在の推奨経路ではありません。

セットアップ（PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

簡単セットアップスクリプト（Windows）:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\scripts\setup_windows.ps1
```

もし `PySide6` を現在の環境に直接入れたい場合:

```powershell
.\scripts\install_pyside_in_current_env.ps1
```

実行方法
- tkinter ベースのメインアプリ（組み込みブラウザはオプション）:

```powershell
python main.py
```

- Qt ベースのアプリ（Qt WebEngine を利用）:

```powershell
python qt_app.py
```

- 単純に URL を pywebview で開くヘルパー:

（組み込みレンダラは `QWebEngineView` に統一されたため、`open_webview.py` は外部ブラウザ起動などの補助用途にとどめます。）

補足
- `main.py` は優先的に RSS（既定: `https://www.4gamer.net/rss/pc/pc_news.xml`）を取得して左側リストに反映します。RSS が取得できない場合はサイトのホームページから候補リンクをスクレイピングしてフォールバックします。
- 組み込みブラウザの動作は環境依存です。`cefpython3` は Python のバージョンとアーキテクチャに合ったビルドが必要で、インストールが難しい場合は `pywebview` を利用してください。

利用上の注意
- ウェブサイトの利用規約・robots.txt を遵守してください。
- 記事本文は著作権があるため再配布や公開に注意してください。

開発者向けメモ
- 主要スクリプト:
	- `main.py`: tkinter ベースのメインアプリ（RSS 取得・組み込み/外部ブラウザ表示）
	- `qt_app.py`: PySide6（QtWebEngine）を使った別 GUI 実装（ジャンル選択あり）
	- `open_webview.py`: `pywebview` で渡した URL を表示する簡易ランチャー

アーキテクチャ
- 本プロジェクトはクリーンアーキテクチャを採用しています。主要層は以下です。
	- `gamer.domain`: ドメインモデル（`Article` など）
	- `gamer.adapters`: 外部との接続（HTTP、RSS 解析など）
	- `gamer.presenter`: プレゼンター（UI とユースケースの仲介）
	- `gamer.ui`: UI 実装（`qt_app.py` が UI に相当）

現在、`qt_app.py` は `gamer.presenter.FeedPresenter` を使って RSS の取得と UI 更新を行います。UI はプレゼンター経由でドメイン/アダプタに依存せず動作します。

ライセンス
- 個人利用・教育目的での利用を想定しています。配布や商用利用を行う場合は各記事の著作権に注意してください。


