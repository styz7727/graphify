"""Permission Center — view whitelists, blocked actions, and recent logs."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QLabel, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget,
)

from jarvis_app.safety import action_log
from jarvis_app import config


class PermissionCenter(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Jarvis — Permission Center")
        self.setMinimumSize(500, 420)
        self.setStyleSheet(_STYLE)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_log_tab(), "📋 Letzte Aktionen")
        tabs.addTab(self._build_whitelist_tab(), "✅ App-Whitelist")
        tabs.addTab(self._build_rules_tab(), "🔒 Regeln")
        layout.addWidget(tabs)

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        entries = action_log.recent(30)
        if not entries:
            layout.addWidget(QLabel("Noch keine Aktionen geloggt."))
            return w
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        inner = QVBoxLayout(container)
        for e in reversed(entries):
            icon = {"safe": "🟢", "confirm": "🟡", "blocked": "🔴"}.get(
                e.get("safety_level", ""), "⚪"
            )
            dec = e.get("decision", "")
            dec_icon = "✓" if dec in ("confirmed", "executed") else ("✗" if dec == "blocked" else "↩")
            ts = e.get("ts", "")[:16].replace("T", " ")
            text = f"{icon} {ts}  [{e.get('intent','?')}]  {e.get('target','')}  {dec_icon}"
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 11px; color: #a0c4ff; padding: 2px 0;")
            inner.addWidget(lbl)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        return w

    def _build_whitelist_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        whitelist = config.app_whitelist()
        layout.addWidget(QLabel("Whitelisted Apps (erfordern Bestätigung):"))
        for name, path in whitelist.items():
            lbl = QLabel(f"  • <b>{name}</b>: {path}")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setStyleSheet("font-size: 11px; color: #e0e0e0;")
            layout.addWidget(lbl)
        layout.addStretch()
        return w

    def _build_rules_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        rules = [
            ("🟢 SAFE",    "Wetter, Notizen lesen/speichern, Git-Log, Hilfe"),
            ("🟡 CONFIRM", "Apps öffnen, Browser, Suche, TradingView, Modus"),
            ("🔴 BLOCKED", "Shell-Befehle, Secrets, Nachrichten senden, Löschen, Installieren"),
        ]
        for level, desc in rules:
            row = QLabel(f"<b>{level}</b>: {desc}")
            row.setTextFormat(Qt.TextFormat.RichText)
            row.setWordWrap(True)
            row.setStyleSheet("font-size: 12px; color: #e0e0e0; padding: 4px 0;")
            layout.addWidget(row)
        layout.addStretch()
        return w


_STYLE = """
QDialog { background-color: #1a1a2e; color: #e0e0e0; }
QTabWidget::pane { border: 1px solid #0f3460; border-radius: 6px; background: #16213e; }
QTabBar::tab { background: #16213e; color: #888; padding: 6px 14px; border-radius: 4px; }
QTabBar::tab:selected { background: #0f3460; color: #e0e0e0; }
QLabel { color: #e0e0e0; }
QScrollArea { background: transparent; border: none; }
"""
