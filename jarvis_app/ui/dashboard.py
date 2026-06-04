"""Dashboard panel: weather, time, reminders, quick-action buttons."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

_QUICK_ACTIONS = [
    ("🌤 Wetter",      "Wie ist das Wetter?"),
    ("💼 Arbeit",      "Starte Arbeitsmodus"),
    ("📚 Lernen",      "Starte Lernmodus"),
    ("📈 Trading",     "Öffne TradingView BTC"),
    ("📝 Notiz",       "Notiere dir: "),
    ("⏰ Erinnerung",  "Erinnere mich an: "),
]


class DashboardWidget(QWidget):
    # Emitted when a quick button is clicked with a pre-filled command
    command_requested = None  # set by overlay to a callable(text)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._weather_text = "Wetter wird geladen…"
        self._build_ui()
        self._start_timers()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 12)

        # ── time ──────────────────────────────────────────────────────────────
        self._time_label = QLabel()
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_label.setStyleSheet(
            "font-size: 36px; font-weight: bold; color: #4ecca3;"
        )
        root.addWidget(self._time_label)

        # ── weather ───────────────────────────────────────────────────────────
        self._weather_label = QLabel(self._weather_text)
        self._weather_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._weather_label.setWordWrap(True)
        self._weather_label.setStyleSheet(
            "font-size: 13px; color: #a0c4ff; background: #0f3460; "
            "border-radius: 8px; padding: 8px;"
        )
        root.addWidget(self._weather_label)

        # ── reminders ─────────────────────────────────────────────────────────
        reminder_title = QLabel("📅 Heute")
        reminder_title.setStyleSheet("font-size: 12px; color: #666; font-weight: bold;")
        root.addWidget(reminder_title)

        self._reminder_area = QScrollArea()
        self._reminder_area.setWidgetResizable(True)
        self._reminder_area.setMaximumHeight(100)
        self._reminder_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._reminder_container = QWidget()
        self._reminder_layout = QVBoxLayout(self._reminder_container)
        self._reminder_layout.setContentsMargins(0, 0, 0, 0)
        self._reminder_layout.setSpacing(2)
        self._reminder_area.setWidget(self._reminder_container)
        root.addWidget(self._reminder_area)

        # ── quick buttons ─────────────────────────────────────────────────────
        quick_title = QLabel("⚡ Schnellzugriff")
        quick_title.setStyleSheet("font-size: 12px; color: #666; font-weight: bold;")
        root.addWidget(quick_title)

        grid = QGridLayout()
        grid.setSpacing(6)
        for i, (label, cmd) in enumerate(_QUICK_ACTIONS):
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet(
                "QPushButton { background:#16213e; color:#e0e0e0; border-radius:6px; "
                "font-size:11px; } QPushButton:hover { background:#0f3460; }"
            )
            btn.clicked.connect(lambda _, c=cmd: self._quick_action(c))
            grid.addWidget(btn, i // 3, i % 3)
        root.addLayout(grid)
        root.addStretch()

    def _start_timers(self) -> None:
        # Clock: every second
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        # Weather: on start + every 30 min
        self._weather_timer = QTimer(self)
        self._weather_timer.timeout.connect(self._refresh_weather)
        self._weather_timer.start(30 * 60 * 1000)
        QTimer.singleShot(500, self._refresh_weather)

        # Reminders: every minute
        self._reminder_timer = QTimer(self)
        self._reminder_timer.timeout.connect(self._refresh_reminders)
        self._reminder_timer.start(60_000)
        QTimer.singleShot(600, self._refresh_reminders)

    def _update_clock(self) -> None:
        from datetime import datetime
        self._time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _refresh_weather(self) -> None:
        from jarvis_app.tools.weather import get_weather
        import threading
        def _fetch():
            result = get_weather()
            self._weather_label.setText(result)
        threading.Thread(target=_fetch, daemon=True).start()

    def _refresh_reminders(self) -> None:
        from jarvis_app.memory.reminders import get_today
        # Clear old
        while self._reminder_layout.count():
            item = self._reminder_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        today = get_today()
        if not today:
            lbl = QLabel("Keine Erinnerungen für heute.")
            lbl.setStyleSheet("color: #555; font-size: 11px;")
            self._reminder_layout.addWidget(lbl)
        for r in today:
            lbl = QLabel(f"• {r['content']} — {r['due_text']}")
            lbl.setStyleSheet("color: #a0c4ff; font-size: 11px;")
            lbl.setWordWrap(True)
            self._reminder_layout.addWidget(lbl)

    def _quick_action(self, cmd: str) -> None:
        if self.command_requested:
            self.command_requested(cmd)
