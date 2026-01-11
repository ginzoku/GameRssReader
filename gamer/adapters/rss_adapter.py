import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from ..adapters.network_requests import get
from ..ports.rss_gateway import RssGateway
from typing import List, Dict, Optional


def _find_local_text(elem, name):
    for child in elem:
        tag = child.tag
        if '}' in tag:
            local = tag.rsplit('}', 1)[1]
        else:
            local = tag
        if local == name:
            return child.text or ''
    return ''


def fetch_rss(url, headers=None):
    resp = get(url, headers=headers)
    items: List[Dict] = []
    root = ET.fromstring(resp.content)
    for elem in root.iter():
        tag = elem.tag
        local = tag.rsplit('}', 1)[1] if '}' in tag else tag
        if local.lower() == 'item':
            title = (_find_local_text(elem, 'title') or '').strip() or '(タイトル取得できず)'
            link = (_find_local_text(elem, 'link') or '').strip()
            pubdate = (_find_local_text(elem, 'pubDate') or '').strip()
            desc_raw = (_find_local_text(elem, 'description') or '').strip()
            desc = ''
            if desc_raw:
                desc = BeautifulSoup(desc_raw, 'html.parser').get_text(' ', strip=True)
            items.append({'title': title, 'link': link, 'pubDate': pubdate, 'description': desc})
    return items


class RssAdapter(RssGateway):
    """Adapter implementing the RssGateway port."""

    def fetch(self, url: str, headers: Optional[Dict] = None):
        return fetch_rss(url, headers=headers)

