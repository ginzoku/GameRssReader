import requests


def get(url, headers=None, timeout=10):
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp
