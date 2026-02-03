"""Gamespark 用 URL 解析ユーティリティ（実験実装）。

元 `url_parser.py` のリネーム版。Gamespark のカテゴリページから
記事リンクと画像 `alt` を抽出する簡易実装を提供します。
"""

import re
from typing import List
from urllib.parse import urljoin, urlparse

from ..adapters.network_requests import get
from bs4 import BeautifulSoup


class GameSparkUrlParser:
    """Gamespark 向け URL 解析ユーティリティ。

    メソッド:
      - extract_article_links(page_url, include_alt=False)
    """

    _pattern = re.compile(r'^/article/\d{4}/\d{2}/\d{2}/\d{6}\.html$')

    @classmethod
    def extract_article_links(cls, page_url: str, headers: dict = None, include_alt: bool = False, allow_robots: bool = False):
        h = headers or {"User-Agent": "GameRssReader/1.0"}
        resp = get(page_url, headers=h, timeout=10, allow_robots=allow_robots)
        soup = BeautifulSoup(resp.content, 'html.parser')
        # Prefer structured news list: find div.news-list and extract
        seen = {}
        try:
            container = soup.find('div', class_='news-list') or soup
            # select highlighted and normal items in document order
            nodes = container.select('.item--highlight, .item--normal')
            for node in nodes:
                try:
                    a = node.find('a', href=True)
                    if not a:
                        continue
                    href = a['href'].strip()
                    abs_url = urljoin(page_url, href)
                    if abs_url in seen:
                        continue
                    # title: prefer <img class="figure" alt="..."> inside the link,
                    # fallback to any <img> alt, then anchor text
                    alt = ''
                    try:
                        img = a.find('img', class_='figure')
                        if img is None:
                            img = a.find('img')
                        if img and img.has_attr('alt'):
                            alt = (img.get('alt') or '').strip()
                    except Exception:
                        alt = ''
                    if not alt:
                        alt = (a.get_text(strip=True) or '')
                    seen[abs_url] = alt
                except Exception:
                    pass
        except Exception:
            seen = {}

        items = [{'url': u, 'alt': seen[u]} for u in seen.keys()]
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
