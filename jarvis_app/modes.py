"""Mode definitions for Jarvis focus modes."""
from __future__ import annotations

MODES: dict[str, dict] = {
    "work": {
        "name": "Arbeitsmodus",
        "apps": ["teams", "vscode"],
        "urls": [],
        "message": "Teams und VS Code werden geöffnet.",
    },
    "learn": {
        "name": "Lernmodus",
        "apps": ["vscode"],
        "urls": [],
        "message": "VS Code ist bereit. Viel Erfolg beim Lernen.",
    },
    "trading": {
        "name": "Tradingmodus",
        "apps": ["chrome"],
        "urls": ["https://www.tradingview.com"],
        "message": "Chrome und TradingView werden geöffnet.",
    },
    "school": {
        "name": "Schulmodus",
        "apps": ["notepad"],
        "urls": [],
        "message": "Notizblock ist geöffnet. Viel Erfolg.",
    },
}
