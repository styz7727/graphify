"""Scrollable HTML chat history widget with JSON persistence."""
from __future__ import annotations

import json
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget, QLabel

from jarvis_app import config
from jarvis_app.safety.redaction import clean

_MAX_DISPLAY = 100   # max bubbles shown at once


class ChatWidget(QScrollArea):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setSpacing(6)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.addStretch()
        self.setWidget(self._container)

        self._history: list[dict] = []
        self._load()

    # ── public API ─────────────────────────────────────────────────────────────

    def add_user(self, text: str) -> None:
        self._add_bubble(clean(text), is_user=True)
        self._history.append({"role": "user", "text": text,
                               "ts": datetime.now().isoformat()})
        self._save()

    def add_jarvis(self, text: str) -> None:
        self._add_bubble(clean(text), is_user=False)
        self._history.append({"role": "jarvis", "text": text,
                               "ts": datetime.now().isoformat()})
        self._save()

    def add_system(self, text: str) -> None:
        label = QLabel(f"<i style='color:#666;font-size:11px'>{text}</i>")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.insertWidget(self._layout.count() - 1, label)
        self._scroll_bottom()

    # ── internals ──────────────────────────────────────────────────────────────

    def _add_bubble(self, text: str, is_user: bool) -> None:
        ts = datetime.now().strftime("%H:%M")
        if is_user:
            html = (
                f'<div style="text-align:right;margin:2px 0">'
                f'<span style="font-size:10px;color:#666">{ts}</span><br>'
                f'<span style="background:#0f3460;color:#e0e0e0;border-radius:10px;'
                f'padding:6px 12px;display:inline-block;max-width:340px">{_esc(text)}</span>'
                f'</div>'
            )
        else:
            html = (
                f'<div style="text-align:left;margin:2px 0">'
                f'<span style="font-size:10px;color:#666">🤖 {ts}</span><br>'
                f'<span style="background:#16213e;color:#e0e0e0;border-radius:10px;'
                f'padding:6px 12px;display:inline-block;max-width:340px">{_esc(text)}</span>'
                f'</div>'
            )
        label = QLabel(html)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setOpenExternalLinks(False)
        self._layout.insertWidget(self._layout.count() - 1, label)
        self._scroll_bottom()

    def _scroll_bottom(self) -> None:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        ))

    def _save(self) -> None:
        try:
            config.CHAT_HISTORY_PATH.write_text(
                json.dumps(self._history[-200:], ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def _load(self) -> None:
        try:
            data = json.loads(config.CHAT_HISTORY_PATH.read_text(encoding="utf-8"))
            for entry in data[-_MAX_DISPLAY:]:
                if entry["role"] == "user":
                    self._add_bubble(entry["text"], is_user=True)
                else:
                    self._add_bubble(entry["text"], is_user=False)
            self._history = data
        except Exception:
            pass


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("\n", "<br>"))
