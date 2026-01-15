"""Gamespark 用 URL 解析ユーティリティ（実験実装）。

元 `url_parser.py` のリネーム版。Gamespark のカテゴリページから
記事リンクと画像 `alt` を抽出する簡易実装を提供します。
"""

import re
from typing import List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class GameSparkUrlParser:
    """Gamespark 向け URL 解析ユーティリティ。

    メソッド:
      - extract_article_links(page_url, include_alt=False)
    """

    _pattern = re.compile(r'^/article/\d{4}/\d{2}/\d{2}/\d{6}\.html$')

    @classmethod
    def extract_article_links(cls, page_url: str, headers: dict = None, include_alt: bool = False):
        h = headers or {"User-Agent": "GameRssReader/1.0"}
        resp = requests.get(page_url, headers=h, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        seen = {}
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            abs_url = urljoin(page_url, href)
            p = urlparse(abs_url)
            if cls._pattern.match(p.path):
                alt = ''
                img = a.find('img')
                if img and img.has_attr('alt'):
                    try:
                        alt = (img.get('alt') or '').strip()
                    except Exception:
                        alt = ''
                seen[abs_url] = alt

        items = [{'url': u, 'alt': seen[u]} for u in sorted(seen.keys())]
        if include_alt:
            return items
        return [i['url'] for i in items]


if __name__ == '__main__':
    test_url = 'https://www.gamespark.jp/category/pc/latest/?page=1'
    try:
        links = GameSparkUrlParser.extract_article_links(test_url, include_alt=True)
        if links:
            for item in links:
                print(item['url'])
                print('  alt:', item['alt'] or '(no alt)')
        else:
            print('No matching links found')
    except Exception as e:
        print('Error:', e)
