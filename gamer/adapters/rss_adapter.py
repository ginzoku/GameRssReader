import urllib.parse
import textwrap
from typing import List
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from gamer.adapters.network_requests import get
from gamer.domain.entities import Article

BASE_URL = "https://www.4gamer.net/"
DEFAULT_RSS = "https://www.4gamer.net/rss/pc/pc_news.xml"


def fetch_candidates() -> List[str]:
    resp = get(BASE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        if any(href.lower().endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js")):
            continue
        url = urllib.parse.urljoin(BASE_URL, href)
        parsed = urllib.parse.urlparse(url)
        if not parsed.netloc:
            continue
        if "4gamer.net" not in parsed.netloc:
            continue
        path = parsed.path.strip("/")
        if not path:
            continue
        if len(path.split("/")) >= 2 or len(a.get_text(strip=True)) > 20:
            links.add(url)
    return list(links)


def fetch_article(url: str) -> Article:
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    title_tag = soup.find("h1") or soup.title
    title = title_tag.get_text(strip=True) if title_tag else "(タイトル取得できず)"
    snippet = None
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) >= 40:
            snippet = text
            break
    if not snippet:
        body_text = soup.get_text(" ", strip=True)
        snippet = body_text[:300]
    snippet = textwrap.shorten(snippet, width=300, placeholder="…")
    return Article(title=title, link=url, description=snippet)


def fetch_full_article(url: str) -> Article:
    resp = get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    title_tag = soup.find("h1") or soup.title
    title = title_tag.get_text(strip=True) if title_tag else "(タイトル取得できず)"
    paras = []
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text:
            paras.append(text)
    if paras:
        body = "\n\n".join(paras)
    else:
        body = soup.get_text(" ", strip=True)
    if len(body) > 20000:
        body = body[:20000] + "\n\n…（省略）"
    return Article(title=title, link=url, body=body)


def fetch_rss(url: str = DEFAULT_RSS) -> List[Article]:
    resp = get(url)
    items = []
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return items

    def find_local_text(elem, name):
        for child in elem:
            tag = child.tag
            if '}' in tag:
                local = tag.rsplit('}', 1)[1]
            else:
                local = tag
            if local == name:
                return child.text or ''
        return ''

    for elem in root.iter():
        tag = elem.tag
        local = tag.rsplit('}', 1)[1] if '}' in tag else tag
        if local.lower() == 'item':
            title = (find_local_text(elem, 'title') or '').strip() or "(タイトル取得できず)"
            link = (find_local_text(elem, 'link') or '').strip()
            pubdate = (find_local_text(elem, 'pubDate') or '').strip()
            desc_raw = (find_local_text(elem, 'description') or '').strip()
            desc = ''
            if desc_raw:
                desc = BeautifulSoup(desc_raw, "html.parser").get_text(" ", strip=True)
            items.append(Article(title=title, link=link, description=desc, pubDate=pubdate))
    return items
