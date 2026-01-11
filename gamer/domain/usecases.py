"""Use cases (application/business logic) for GameRssReader.

このモジュールは外部（adapters）をポートとして使い、UI 層から呼ばれる高レベル操作を提供します。
"""
from typing import List, Optional, Tuple
import random

from gamer.domain.entities import Article
from gamer.adapters.rss_adapter import fetch_rss, fetch_article, fetch_full_article, fetch_candidates


def get_rss_items(rss_url: Optional[str] = None) -> List[Article]:
    """RSS を取得して Article のリストを返す。

    rss_url を None にすると adapter 側のデフォルトを使う。
    """
    if rss_url:
        return fetch_rss(rss_url)
    return fetch_rss()


def prepare_feed_and_initial_article(rss_url: Optional[str] = None) -> Tuple[List[Article], Optional[Article]]:
    """RSS を取得し、一覧と最初に表示する Article を返す。

    - RSS 項目が存在する場合は最初の項目を返す（description がなければ個別取得して補完）
    - RSS 項目が空の場合はホームページから候補をスクレイピングしてランダムに1件取得して返す
    """
    items = get_rss_items(rss_url)
    if items:
        first = items[0]
        if (not first.description or first.description.strip() == "") and first.link:
            try:
                fetched = fetch_article(first.link)
                if fetched and fetched.description:
                    first = Article(title=fetched.title or first.title, link=first.link, description=fetched.description, pubDate=first.pubDate, body=fetched.body)
            except Exception:
                pass
        return items, first

    # フォールバック: ホームページから候補抽出
    candidates = fetch_candidates()
    if not candidates:
        return [], None
    url = random.choice(candidates)
    art = fetch_article(url)
    return [], art


def get_full_article(url: str) -> Article:
    """URL から全文を取得して Article を返す。"""
    return fetch_full_article(url)
