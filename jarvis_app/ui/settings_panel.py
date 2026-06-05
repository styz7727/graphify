"""Jarvis settings dialog — wake word toggle and preferences."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QLabel, QCheckBox, QVBoxLayout, QPushButton,
)

from jarvis_app import config


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Jarvis — Einstellungen")
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog   { background: #1a1a2e; }
            QLabel    { color: #e0e0e0; }
            QCheckBox { color: #e0e0e0; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px;
                                   border: 1px solid #0f3460; background: #16213e; }
            QCheckBox::indicator:checked { background: #4ecca3; border-color: #4ecca3; }
        """)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # ── section header ────────────────────────────────────────────────────
        hdr = QLabel("Wake Word")
        hdr.setStyleSheet("font-size: 13px; font-weight: bold; color: #4ecca3;")
        layout.addWidget(hdr)

        # ── toggle ────────────────────────────────────────────────────────────
        self._wake_chk = QCheckBox("'Hey Jarvis' aktivieren")
        self._wake_chk.setChecked(config.wake_word_enabled())
        layout.addWidget(self._wake_chk)

        # ── privacy note ──────────────────────────────────────────────────────
        note = QLabel(
            "Das Mikrofon lauscht lokal nur auf das Aktivierungswort.\n"
            "Es werden keine Aufnahmen gespeichert oder übertragen.\n"
            "Erst nach 'Hey Jarvis' wird der Befehl aufgenommen.\n"
            "Das Mikrofon-Icon leuchtet grün, wenn Wake Word aktiv ist."
        )
        note.setStyleSheet("color: #666; font-size: 11px; line-height: 1.5;")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()

        # ── save button ───────────────────────────────────────────────────────
        save_btn = QPushButton("Speichern & Schließen")
        save_btn.setStyleSheet(
            "QPushButton { background: #4ecca3; color: #1a1a2e; border-radius: 8px; "
            "padding: 8px 20px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: #38b89a; }"
        )
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _save(self) -> None:
        config.set_wake_word_enabled(self._wake_chk.isChecked())
        self.accept()
