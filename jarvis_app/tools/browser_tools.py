"""Open URLs or searches in the default browser."""
from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

_SEARCH_BASE = "https://duckduckgo.com/?q="


def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Webseite geöffnet: {url}"


def web_search(query: str) -> str:
    url = _SEARCH_BASE + quote_plus(query)
    webbrowser.open(url)
    return f"Suche geöffnet: {query}"
