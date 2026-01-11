import requests

HEADERS = {"User-Agent": "4games-scraper/1.0 (+https://example.com)"}


def get(url: str, timeout: int = 10) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp
