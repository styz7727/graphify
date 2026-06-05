"""Jarvis settings dialog — voice, TTS, weather, system, API key status."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from jarvis_app import config

# German edge-tts voices that work well with Jarvis
_TTS_VOICES = [
    ("de-DE-ConradNeural",  "Conrad (DE, männlich) — Standard"),
    ("de-DE-KatjaNeural",   "Katja (DE, weiblich)"),
    ("de-DE-KillianNeural", "Killian (DE, männlich)"),
    ("de-AT-JonasNeural",   "Jonas (AT, männlich)"),
    ("de-CH-JanNeural",     "Jan (CH, männlich)"),
    ("de-CH-LeniNeural",    "Leni (CH, weiblich)"),
]


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Jarvis — Einstellungen")
        self.setFixedWidth(460)
        self.setStyleSheet(_STYLE)
        self._build_ui()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 12)
        outer.setSpacing(0)

        # scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #1a1a2e; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: #1a1a2e;")
        vl = QVBoxLayout(content)
        vl.setContentsMargins(24, 20, 24, 8)
        vl.setSpacing(16)

        self._add_section(vl, "Spracheingabe")
        self._build_voice_section(vl)

        self._add_section(vl, "Sprachausgabe (TTS)")
        self._build_tts_section(vl)

        self._add_section(vl, "Wetter")
        self._build_weather_section(vl)

        self._add_section(vl, "System")
        self._build_system_section(vl)

        self._add_section(vl, "API Key — Status")
        self._build_apikey_section(vl)

        vl.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # ── save button ───────────────────────────────────────────────────────
        save_btn = QPushButton("Speichern & Schließen")
        save_btn.setStyleSheet(
            "QPushButton { background:#4ecca3; color:#1a1a2e; border-radius:8px; "
            "padding:9px 24px; font-size:13px; font-weight:bold; margin:0 24px; }"
            "QPushButton:hover { background:#38b89a; }"
        )
        save_btn.clicked.connect(self._save)
        outer.addWidget(save_btn)

    # ── sections ──────────────────────────────────────────────────────────────

    def _add_section(self, layout: QVBoxLayout, title: str) -> None:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#4ecca3; "
            "border-bottom:1px solid #0f3460; padding-bottom:3px;"
        )
        layout.addWidget(lbl)

    def _build_voice_section(self, vl: QVBoxLayout) -> None:
        self._wake_chk = QCheckBox("'Hey Jarvis' Wake Word aktivieren")
        self._wake_chk.setChecked(config.wake_word_enabled())
        vl.addWidget(self._wake_chk)

        note = QLabel(
            "Mikrofon lauscht lokal nur auf das Aktivierungswort.\n"
            "Kein Audio wird gespeichert oder übertragen.\n"
            "Mic-Icon leuchtet grün wenn Wake Word aktiv ist."
        )
        note.setStyleSheet("color:#555; font-size:11px;")
        note.setWordWrap(True)
        vl.addWidget(note)

        thr_row = QWidget()
        th = QHBoxLayout(thr_row)
        th.setContentsMargins(0, 0, 0, 0)
        th.setSpacing(8)
        th.addWidget(QLabel("Erkennungs-Schwelle:"))
        self._wake_thr = QDoubleSpinBox()
        self._wake_thr.setRange(0.1, 1.0)
        self._wake_thr.setSingleStep(0.05)
        self._wake_thr.setDecimals(2)
        self._wake_thr.setValue(config.wake_word_threshold())
        self._wake_thr.setStyleSheet(
            "QDoubleSpinBox { background:#16213e; color:#e0e0e0; "
            "border:1px solid #0f3460; border-radius:4px; padding:4px 8px; }"
        )
        self._wake_thr.setFixedWidth(90)
        th.addWidget(self._wake_thr)
        th.addWidget(QLabel("(0.1 = empfindlich · 1.0 = streng)"))
        th.addStretch()
        vl.addWidget(thr_row)

    def _build_tts_section(self, vl: QVBoxLayout) -> None:
        self._tts_chk = QCheckBox("Sprachausgabe aktivieren")
        self._tts_chk.setChecked(config.tts_enabled())
        vl.addWidget(self._tts_chk)

        voice_row = QWidget()
        vh = QHBoxLayout(voice_row)
        vh.setContentsMargins(0, 0, 0, 0)
        vh.setSpacing(8)
        vh.addWidget(QLabel("Stimme:"))
        self._voice_cb = QComboBox()
        self._voice_cb.setStyleSheet(
            "QComboBox { background:#16213e; color:#e0e0e0; border:1px solid #0f3460; "
            "border-radius:4px; padding:4px 8px; }"
            "QComboBox::drop-down { border:none; }"
            "QComboBox QAbstractItemView { background:#16213e; color:#e0e0e0; "
            "selection-background-color:#0f3460; }"
        )
        current_voice = config.tts_voice()
        for val, label in _TTS_VOICES:
            self._voice_cb.addItem(label, userData=val)
            if val == current_voice:
                self._voice_cb.setCurrentIndex(self._voice_cb.count() - 1)
        vh.addWidget(self._voice_cb, stretch=1)
        vh.addStretch()
        vl.addWidget(voice_row)

    def _build_weather_section(self, vl: QVBoxLayout) -> None:
        row = QWidget()
        rh  = QHBoxLayout(row)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(8)
        rh.addWidget(QLabel("Stadt:"))
        self._city_edit = QLineEdit(config.city())
        self._city_edit.setPlaceholderText("z.B. Zürich")
        self._city_edit.setStyleSheet(
            "QLineEdit { background:#16213e; color:#e0e0e0; border:1px solid #0f3460; "
            "border-radius:4px; padding:4px 10px; }"
            "QLineEdit:focus { border-color:#4ecca3; }"
        )
        self._city_edit.setFixedWidth(180)
        rh.addWidget(self._city_edit)
        rh.addStretch()
        vl.addWidget(row)

    def _build_system_section(self, vl: QVBoxLayout) -> None:
        from jarvis_app.autostart import is_autostart_enabled
        self._autostart_chk = QCheckBox("Jarvis beim Windows-Start automatisch starten")
        self._autostart_chk.setChecked(is_autostart_enabled())
        vl.addWidget(self._autostart_chk)

        note = QLabel("Trägt einen Eintrag in HKCU\\...\\Run ein (kein Admin nötig).")
        note.setStyleSheet("color:#555; font-size:11px;")
        vl.addWidget(note)

        test_btn = QPushButton("🩺 Startup-Test jetzt ausführen")
        test_btn.setStyleSheet(
            "QPushButton { background:#16213e; color:#4ecca3; border:1px solid #0f3460; "
            "border-radius:6px; padding:6px 14px; font-size:12px; }"
            "QPushButton:hover { background:#0f3460; }"
        )
        test_btn.clicked.connect(self._open_debug)
        vl.addWidget(test_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def _build_apikey_section(self, vl: QVBoxLayout) -> None:
        import os
        found = False
        for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
            key = os.environ.get(var, "")
            if key and len(key) > 8:
                masked = f"...{key[-4:]}"
                lbl = QLabel(f"  {var}: gesetzt ({masked}, Länge {len(key)})")
                lbl.setStyleSheet("color:#4ecca3; font-size:11px;")
                vl.addWidget(lbl)
                found = True

        if not found:
            lbl = QLabel("Kein API-Key gefunden — LLM-Abfragen nicht verfügbar.")
            lbl.setStyleSheet("color:#e05555; font-size:11px;")
            vl.addWidget(lbl)

        hint = QLabel(
            "Key vor dem Start setzen:\n"
            "  PowerShell:  $env:ANTHROPIC_API_KEY='sk-...'\n"
            "  Cmd:         set ANTHROPIC_API_KEY=sk-...\n"
            "Keys werden nie gespeichert oder angezeigt."
        )
        hint.setStyleSheet("color:#555; font-size:11px;")
        hint.setWordWrap(True)
        vl.addWidget(hint)

    # ── save / actions ────────────────────────────────────────────────────────

    def _save(self) -> None:
        config.set_wake_word_enabled(self._wake_chk.isChecked())
        config.set_wake_word_threshold(self._wake_thr.value())
        config.set_("tts_enabled", "true" if self._tts_chk.isChecked() else "false")
        config.set_tts_voice(self._voice_cb.currentData())
        config.set_city(self._city_edit.text().strip() or "Zürich")

        from jarvis_app.autostart import set_autostart
        set_autostart(self._autostart_chk.isChecked())

        self.accept()

    def _open_debug(self) -> None:
        from jarvis_app.ui.debug_panel import DebugPanel
        self.accept()   # close settings first
        dlg = DebugPanel(self.parent())
        dlg.exec()


# ── stylesheet ────────────────────────────────────────────────────────────────

_STYLE = """
QDialog   { background: #1a1a2e; }
QLabel    { color: #e0e0e0; font-size: 12px; }
QCheckBox { color: #e0e0e0; spacing: 8px; font-size: 12px; }
QCheckBox::indicator { width:18px; height:18px; border-radius:4px;
                       border:1px solid #0f3460; background:#16213e; }
QCheckBox::indicator:checked { background:#4ecca3; border-color:#4ecca3; }
"""
