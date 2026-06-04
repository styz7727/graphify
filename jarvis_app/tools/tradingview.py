"""Map ticker symbols to TradingView chart URLs."""
from __future__ import annotations

import webbrowser

_BASE = "https://www.tradingview.com/chart/?symbol="

_SYMBOL_MAP: dict[str, str] = {
    "btc":      "BINANCE:BTCUSDT",
    "bitcoin":  "BINANCE:BTCUSDT",
    "eth":      "BINANCE:ETHUSDT",
    "ethereum": "BINANCE:ETHUSDT",
    "sol":      "BINANCE:SOLUSDT",
    "aapl":     "NASDAQ:AAPL",
    "apple":    "NASDAQ:AAPL",
    "msft":     "NASDAQ:MSFT",
    "microsoft":"NASDAQ:MSFT",
    "nvda":     "NASDAQ:NVDA",
    "nvidia":   "NASDAQ:NVDA",
    "tsla":     "NASDAQ:TSLA",
    "tesla":    "NASDAQ:TSLA",
    "spx":      "SP:SPX",
    "sp500":    "SP:SPX",
    "dax":      "XETR:DAX",
    "gold":     "TVC:GOLD",
    "oil":      "TVC:USOIL",
}


def open_chart(symbol: str) -> str:
    normalized = _SYMBOL_MAP.get(symbol.lower(), symbol.upper())
    url = _BASE + normalized
    webbrowser.open(url)
    return f"TradingView geöffnet: {normalized}"


def normalize(symbol: str) -> str:
    return _SYMBOL_MAP.get(symbol.lower(), symbol.upper())
