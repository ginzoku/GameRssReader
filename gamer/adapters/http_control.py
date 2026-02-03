"""
Simple HTTP control utilities: robots.txt check and per-host rate limiter.
Used by adapters and utils instead of direct requests.get.
"""
import time
import threading
from urllib.parse import urlparse
from urllib import robotparser
from typing import Optional

import requests

_lock = threading.Lock()
_robots_cache = {}
_last_request = {}

DEFAULT_USER_AGENT = "GameRssReader/1.0 (+https://example.com)"
MIN_INTERVAL = 1.0  # seconds per host


def _get_host(url: str) -> str:
    p = urlparse(url)
    return p.netloc.lower()


def can_fetch(url: str, user_agent: Optional[str] = None) -> bool:
    ua = user_agent or DEFAULT_USER_AGENT
    host = _get_host(url)
    with _lock:
        rp = _robots_cache.get(host)
        if rp is None:
            rp = robotparser.RobotFileParser()
            try:
                robots_url = f"{urlparse(url).scheme}://{host}/robots.txt"
                rp.set_url(robots_url)
                rp.read()
            except Exception:
                # if robots can't be read, default to allowing
                rp = None
            _robots_cache[host] = rp
    # if rp is None we assume allowed
    if rp is None:
        return True
    try:
        return rp.can_fetch(ua, url)
    except Exception:
        return True


def wait_for_slot(url: str) -> None:
    host = _get_host(url)
    with _lock:
        last = _last_request.get(host)
        now = time.time()
        if last is None:
            _last_request[host] = now
            return
        elapsed = now - last
        if elapsed >= MIN_INTERVAL:
            _last_request[host] = now
            return
        # need to wait outside lock
        wait = MIN_INTERVAL - elapsed
    time.sleep(wait)
    with _lock:
        _last_request[host] = time.time()


def get(url: str, headers: Optional[dict] = None, timeout: int = 10, allow_robots: bool = False):
    """Perform GET with robots check and rate limiting.

    If `allow_robots` is True, robots.txt check is skipped (use with caution).
    Raises PermissionError if disallowed by robots and `allow_robots` is False.
    """
    if not allow_robots:
        if not can_fetch(url, headers.get('User-Agent') if headers else None):
            raise PermissionError(f"Fetching disallowed by robots.txt: {url}")
    wait_for_slot(url)
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp
