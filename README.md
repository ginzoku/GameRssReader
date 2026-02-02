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

# 4Gamer 記事ビューワ（GameRssReader）

シンプルなデスクトップ向け RSS/記事ビューワです。4Gamer の RSS を取得して一覧表示し、選択した記事を組み込みブラウザまたは外部ブラウザで表示します。

主な機能
- RSS フィードの取得と一覧表示（複数ジャンルに対応）
- 記事本文の要約（サニタイズ済みテキスト）表示
- 組み込みブラウザ表示（`QWebEngineView` を優先）
- Qt ベースの別アプリケーション（`qt_app.py`）を含む

対応プラットフォーム
- Windows（開発・動作確認済み）

**要件**
- Python: 3.8 以上（3.9/3.10/3.11 を推奨）
- OS: Windows
- パッケージマネージャ: `pip`
- 必須パッケージ: `requests`, `beautifulsoup4`
- オプションパッケージ:
	- `PySide6` — `qt_app.py`（Qt + QtWebEngine）を実行する場合に必要
	- `cefpython3` — 埋め込みCEFを利用したい場合（Python のバージョン/アーキテクチャ依存）
	- `pywebview` — 軽量な組み込みWebViewの代替

**注意**: `main.py` は起動時に `PySide6` の有無をチェックし、無い場合は例外で停止します（自動インストールは行いません）。付属のスクリプト `scripts/setup_windows.ps1` や `scripts/install_pyside_in_current_env.ps1` を使って手動でセットアップしてください。

---

**セットアップ（推奨: PowerShell）**

```powershell
# 仮想環境作成 + 有効化
python -m venv .venv
& .venv\Scripts\Activate.ps1

# pip を最新にして依存をインストール
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Qt アプリを使う場合 (PySide6 が requirements.txt に含まれています)
# 既存環境に直接入れたい場合はスクリプトを使う:
.\scripts\install_pyside_in_current_env.ps1
```

簡易セットアップスクリプト（Windows）:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\scripts\setup_windows.ps1
```

---

**実行方法**

- tkinter ベースのメインアプリ:

```powershell
python main.py
```

- Qt ベースのアプリ（QtWebEngine を使用）:

```powershell
python qt_app.py
```

---

補足
- `requirements.txt` には `requests`, `beautifulsoup4`, `PySide6` が記載されています（PySide6 は Qt GUI を使う場合に必要）。
- `cefpython3` はバイナリと Python のバージョン/アーキテクチャに依存するため、必要な場合は公式ドキュメントに従ってください。
- ウェブサイトの利用規約・robots.txt を遵守してください。

開発者向けメモ
- 主要スクリプト:
	- `main.py`: tkinter ベースのメインアプリ（RSS 取得・組み込み/外部ブラウザ表示）
	- `qt_app.py`: PySide6（QtWebEngine）を使った別 GUI 実装
	- `open_webview.py`: `pywebview` 等を使う簡易ランチャー（補助用途）

アーキテクチャ
- 本プロジェクトはクリーンアーキテクチャを採用しています。主要層は以下です。
	- `gamer.domain`: ドメインモデル
	- `gamer.adapters`: 外部との接続（HTTP、RSS 解析など）
	- `gamer.presenter`: プレゼンター（UI とユースケースの仲介）
	- `gamer.ui`: UI 実装

ライセンス
- 個人利用・教育目的を想定しています。商用利用はご遠慮ください。



