"""Main Jarvis overlay — frameless, always-on-top, dark theme."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from jarvis_app.ui.chat import ChatWidget
from jarvis_app.ui.dashboard import DashboardWidget
from jarvis_app.worker import ResponseWorker


class Overlay(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._drag_pos: QPoint | None = None
        self._worker: ResponseWorker | None = None
        self._ptw = None          # PushToTalkWorker, started after show()
        self._setup_window()
        self._build_ui()
        self._position_window()

    # ── window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowTitle("Jarvis")
        self.setMinimumSize(QSize(500, 580))
        self.resize(500, 600)
        self.setStyleSheet("background: #1a1a2e; font-family: 'Segoe UI', sans-serif;")

    def _position_window(self) -> None:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        self._card = QWidget()
        self._card.setObjectName("card")
        self._card.setStyleSheet("""
            QWidget#card {
                background-color: #1a1a2e;
                border-radius: 14px;
                border: 1px solid #0f3460;
            }
        """)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        card_layout.addWidget(self._build_title_bar())
        card_layout.addWidget(self._build_tabs(), stretch=1)
        card_layout.addWidget(self._build_input_bar())

        outer.addWidget(self._card)

    def _build_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet("background: #16213e; border-radius: 14px 14px 0 0;")
        bar.mousePressEvent   = self._title_mouse_press
        bar.mouseMoveEvent    = self._title_mouse_move
        bar.mouseReleaseEvent = self._title_mouse_release

        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 0, 10, 0)

        icon = QLabel("🤖")
        icon.setStyleSheet("font-size: 18px;")
        title = QLabel("Jarvis")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4ecca3;")

        perm_btn = QPushButton("🔒")
        perm_btn.setFixedSize(28, 28)
        perm_btn.setToolTip("Permission Center")
        perm_btn.setStyleSheet(_ICON_BTN_STYLE)
        perm_btn.clicked.connect(self._show_permission_center)

        hide_btn = QPushButton("—")
        hide_btn.setFixedSize(28, 28)
        hide_btn.setStyleSheet(_ICON_BTN_STYLE)
        hide_btn.clicked.connect(self.hide)

        h.addWidget(icon)
        h.addWidget(title)
        h.addStretch()
        h.addWidget(perm_btn)
        h.addWidget(hide_btn)
        return bar

    def _build_tabs(self) -> QTabWidget:
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #1a1a2e; }
            QTabBar::tab { background: #16213e; color: #888; padding: 6px 16px; }
            QTabBar::tab:selected { background: #1a1a2e; color: #4ecca3;
                                    border-bottom: 2px solid #4ecca3; }
        """)
        self._chat = ChatWidget()
        self._dashboard = DashboardWidget()
        self._dashboard.command_requested = self._submit_from_dashboard

        self._tabs.addTab(self._dashboard, "🏠 Dashboard")
        self._tabs.addTab(self._chat, "💬 Chat")
        return self._tabs

    def _build_input_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background: #16213e; border-radius: 0 0 14px 14px;")

        v = QVBoxLayout(bar)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(3)

        # ── status line (voice feedback) ──────────────────────────────────────
        self._voice_status = QLabel("F9 halten zum Sprechen")
        self._voice_status.setStyleSheet(
            "color: #555; font-size: 11px; padding: 0 2px;"
        )
        v.addWidget(self._voice_status)

        # ── input row ─────────────────────────────────────────────────────────
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(36, 36)
        self._mic_btn.setToolTip("F9 halten zum Sprechen")
        self._mic_btn.setStyleSheet(_MIC_IDLE_STYLE)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Schreibe oder halte F9 zum Sprechen…")
        self._input.setStyleSheet(
            "QLineEdit { background:#1a1a2e; border:1px solid #0f3460; border-radius:8px; "
            "padding:6px 12px; color:#e0e0e0; font-size:13px; }"
            "QLineEdit:focus { border-color:#4ecca3; }"
        )
        self._input.returnPressed.connect(self._on_send)

        send_btn = QPushButton("→")
        send_btn.setFixedSize(36, 36)
        send_btn.setStyleSheet(
            "QPushButton { background:#4ecca3; color:#1a1a2e; border-radius:8px; "
            "font-size:16px; font-weight:bold; } QPushButton:hover { background:#38b89a; }"
        )
        send_btn.clicked.connect(self._on_send)

        h.addWidget(self._mic_btn)
        h.addWidget(self._input)
        h.addWidget(send_btn)
        v.addWidget(row)
        return bar

    # ── push-to-talk ─────────────────────────────────────────────────────────

    def start_push_to_talk(self) -> None:
        """Call once after the window is shown to start the global F9 listener."""
        from jarvis_app.ui.push_to_talk import PushToTalkWorker
        self._ptw = PushToTalkWorker()
        self._ptw.recording_started.connect(self._on_recording_started)
        self._ptw.recording_stopped.connect(self._on_recording_stopped)
        self._ptw.transcription_ready.connect(self._on_voice_text)
        self._ptw.status_message.connect(self._on_voice_status)
        self._ptw.start()

    def _on_recording_started(self) -> None:
        self._mic_btn.setStyleSheet(_MIC_ACTIVE_STYLE)
        self._voice_status.setText("🔴 Aufnahme läuft… F9 loslassen zum Senden")
        self._voice_status.setStyleSheet("color: #e05555; font-size: 11px; padding: 0 2px;")

    def _on_recording_stopped(self) -> None:
        self._mic_btn.setStyleSheet(_MIC_IDLE_STYLE)
        self._voice_status.setText("⏳ Transkribiere…")
        self._voice_status.setStyleSheet("color: #888; font-size: 11px; padding: 0 2px;")

    def _on_voice_text(self, text: str) -> None:
        self._voice_status.setText("F9 halten zum Sprechen")
        self._voice_status.setStyleSheet("color: #555; font-size: 11px; padding: 0 2px;")
        self._input.setText(text)
        self._on_send()

    def _on_voice_status(self, msg: str) -> None:
        self._voice_status.setText(msg)
        self._voice_status.setStyleSheet("color: #888; font-size: 11px; padding: 0 2px;")
        # Reset to default hint after 4 seconds
        QTimer.singleShot(4000, lambda: self._voice_status.setText("F9 halten zum Sprechen"))

    # ── message handling ──────────────────────────────────────────────────────

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text or (self._worker and self._worker.isRunning()):
            return
        self._input.clear()
        self._tabs.setCurrentIndex(1)
        self._chat.add_user(text)
        self._chat.add_system("⏳ Jarvis denkt…")
        self._start_worker(text)

    def _submit_from_dashboard(self, cmd: str) -> None:
        self._input.setText(cmd)
        if not cmd.endswith(": "):
            self._on_send()
        else:
            self._input.setFocus()

    def _start_worker(self, text: str) -> None:
        self._worker = ResponseWorker(text)
        self._worker.response_ready.connect(self._on_response)
        self._worker.needs_confirmation.connect(self._on_confirm)
        self._worker.start()

    def _on_response(self, question: str, answer: str) -> None:
        self._chat.add_jarvis(answer)

    def _on_confirm(self, description: str) -> None:
        from jarvis_app.safety.confirmation import ConfirmationDialog
        dialog = ConfirmationDialog(description, parent=self)
        dialog.exec()
        if self._worker:
            self._worker.set_confirmed(dialog.confirmed)

    # ── permission center ─────────────────────────────────────────────────────

    def _show_permission_center(self) -> None:
        from jarvis_app.ui.permission_center import PermissionCenter
        dlg = PermissionCenter(parent=self)
        dlg.exec()

    # ── drag to move ──────────────────────────────────────────────────────────

    def _title_mouse_press(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _title_mouse_move(self, event) -> None:
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _title_mouse_release(self, event) -> None:
        self._drag_pos = None

    # ── key events ────────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


# ── styles ────────────────────────────────────────────────────────────────────

_ICON_BTN_STYLE = (
    "QPushButton { background: transparent; color: #888; border: none; "
    "border-radius: 4px; font-size: 13px; }"
    "QPushButton:hover { background: #0f3460; color: #e0e0e0; }"
)

_MIC_IDLE_STYLE = (
    "QPushButton { background: transparent; border: 1px solid #0f3460; "
    "border-radius: 8px; font-size: 16px; }"
    "QPushButton:hover { border-color: #4ecca3; }"
)

_MIC_ACTIVE_STYLE = (
    "QPushButton { background: #3a0000; border: 2px solid #e05555; "
    "border-radius: 8px; font-size: 16px; }"
)
