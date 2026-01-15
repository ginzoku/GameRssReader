"""Automaton 用 URL 解析ユーティリティ。

このモジュールは Automaton のカテゴリページや検索結果ページから
リンクを抽出するための実験的ユーティリティを提供します。
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urljoin


class AutomatonUrlParser:
    """Automaton サイト向けの URL 解析クラス。

    メソッド:
      - extract_dynamic_media_links(page_url) -> List[Dict]
        `<a>` 要素のうちクラス名のいずれかが `ct-dynamic-media` で始まる要素を取得し、
        `{'url': <絶対URL>, 'title': <aria-label または 空文字>}` を返します。
    """

    @classmethod
    def extract_dynamic_media_links(cls, page_url: str, headers: dict = None) -> List[Dict]:
        # kept for backward-compat; prefer using extract_post310463_articles for the new spec
        h = headers or {"User-Agent": "GameRssReader/1.0"}
        resp = requests.get(page_url, headers=h, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        out: List[Dict] = []
        for a in soup.find_all('a', href=True):
            classes = a.get('class') or []
            try:
                if any(str(c).startswith('ct-dynamic-media') for c in classes):
                    href = a['href'].strip()
                    url = urljoin(page_url, href)
                    title = a.get('aria-label') or ''
                    out.append({'url': url, 'title': title})
            except Exception:
                continue
        return out

    @classmethod
    def extract_post310463_articles(cls, page_url: str, headers: dict = None) -> List[Dict]:
        """新仕様:

        - ページ内の `article` 要素のうちクラスに `post-310463` を含む要素を探す
        - その要素配下にあるすべての `article` 要素を取得する
        - 各取得した `article` の中で最初に見つかる `<a href>` を取り、その
          `href` を `url`、アンカー内のテキストを `title` として返す
        """
        h = headers or {"User-Agent": "GameRssReader/1.0"}
        resp = requests.get(page_url, headers=h, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        results: List[Dict] = []

        # find article(s) that include class token 'post-310463'
        candidates = []
        for art in soup.find_all('article'):
            cls_attr = art.get('class') or []
            try:
                tokens = cls_attr if isinstance(cls_attr, list) else str(cls_attr).split()
            except Exception:
                tokens = []
            if 'post-310463' in tokens:
                candidates.append(art)

        if not candidates:
            return results

        # use first matched parent article
        parent = candidates[0]
        nested = parent.find_all('article')
        for na in nested:
            # find first anchor whose class starts with 'ct-dynamic-media'
            target_a = None
            for a in na.find_all('a', href=True):
                cls_attr = a.get('class') or []
                try:
                    tokens = cls_attr if isinstance(cls_attr, list) else str(cls_attr).split()
                except Exception:
                    tokens = []
                if any(str(c).startswith('ct-dynamic-media') for c in tokens):
                    target_a = a
                    break
            if not target_a:
                continue
            href = target_a['href'].strip()
            url = urljoin(page_url, href)
            # use aria-label as title if present
            title = target_a.get('aria-label') or ''
            results.append({'url': url, 'title': title})

        return results


if __name__ == '__main__':
    test_url = 'https://automaton-media.com/pc-steam-epic-games-store-gog/?query-19d0b21f=1'
    try:
        items = AutomatonUrlParser.extract_post310463_articles(test_url)
        if not items:
            print('No matching article items found')
        for i, it in enumerate(items[:20], start=1):
            print(f"{i}. {it['title'] or '(no title)'}")
            print('   ' + it['url'])
    except Exception as e:
        print('Error:', e)

