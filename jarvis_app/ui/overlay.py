"""Main Jarvis overlay — frameless, always-on-top, dark theme."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint, QSize, QTimer, QThread, pyqtSignal as Signal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from jarvis_app.ui.chat import ChatWidget
from jarvis_app.ui.dashboard import DashboardWidget
from jarvis_app.worker import ResponseWorker


# ── Helper thread: auto-record + transcribe after wake word ──────────────────

class _WakeAutoThread(QThread):
    """Records speech after wake word detection, then transcribes and emits text."""

    transcription_ready = Signal(str)
    status_message      = Signal(str)

    def run(self) -> None:
        from jarvis_app import voice
        self.status_message.emit("🔴 Aufnahme läuft… (spreche deinen Befehl)")
        audio = voice.record_until_silence(max_duration=10.0, silence_duration=2.0)
        if audio is None or len(audio) < voice._SAMPLE_RATE * 0.3:
            self.status_message.emit("Kein Befehl gehört — nochmal 'Hey Jarvis' sagen")
            return
        self.status_message.emit("⏳ Transkribiere…")
        text = voice.transcribe(audio)
        if text:
            self.transcription_ready.emit(text)
        else:
            self.status_message.emit("Kein Text erkannt — nochmal versuchen")


# ── Main overlay window ───────────────────────────────────────────────────────

class Overlay(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._drag_pos: QPoint | None = None
        self._worker: ResponseWorker | None = None
        self._ptw     = None   # PushToTalkWorker
        self._wwl     = None   # WakeWordListener
        self._auto    = None   # _WakeAutoThread
        self._pulse_timer: QTimer | None = None
        self._pulse_state: bool = False
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
        x = screen.x() + (screen.width()  - self.width())  // 2
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

        icon  = QLabel("🤖")
        icon.setStyleSheet("font-size: 18px;")
        title = QLabel("Jarvis")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4ecca3;")
        ver_lbl = QLabel("v6")
        ver_lbl.setStyleSheet("font-size: 10px; color: #4ecca3; margin-left: 2px; margin-top: 4px; opacity: 0.6;")

        perm_btn = QPushButton("🔒")
        perm_btn.setFixedSize(28, 28)
        perm_btn.setToolTip("Permission Center")
        perm_btn.setStyleSheet(_ICON_BTN_STYLE)
        perm_btn.clicked.connect(self._show_permission_center)

        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(28, 28)
        settings_btn.setToolTip("Einstellungen")
        settings_btn.setStyleSheet(_ICON_BTN_STYLE)
        settings_btn.clicked.connect(self._show_settings)

        debug_btn = QPushButton("🐛")
        debug_btn.setFixedSize(28, 28)
        debug_btn.setToolTip("Debug & Diagnose")
        debug_btn.setStyleSheet(_ICON_BTN_STYLE)
        debug_btn.clicked.connect(self._show_debug_panel)

        hide_btn = QPushButton("—")
        hide_btn.setFixedSize(28, 28)
        hide_btn.setStyleSheet(_ICON_BTN_STYLE)
        hide_btn.clicked.connect(self.hide)

        h.addWidget(icon)
        h.addWidget(title)
        h.addWidget(ver_lbl)
        h.addStretch()
        h.addWidget(perm_btn)
        h.addWidget(settings_btn)
        h.addWidget(debug_btn)
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
        self._chat      = ChatWidget()
        self._dashboard = DashboardWidget()
        self._dashboard.command_requested = self._submit_from_dashboard

        self._tabs.addTab(self._dashboard, "🏠 Dashboard")
        self._tabs.addTab(self._chat,      "💬 Chat")
        return self._tabs

    def _build_input_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background: #16213e; border-radius: 0 0 14px 14px;")

        v = QVBoxLayout(bar)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(3)

        # ── mic status line ───────────────────────────────────────────────────
        self._voice_status = QLabel("F9 halten zum Sprechen")
        self._voice_status.setStyleSheet("color: #555; font-size: 11px; padding: 0 2px;")
        v.addWidget(self._voice_status)

        # ── input row ─────────────────────────────────────────────────────────
        row = QWidget()
        h   = QHBoxLayout(row)
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

    # ── push-to-talk (F9) ────────────────────────────────────────────────────

    def start_push_to_talk(self) -> None:
        """Call once after show() to start the global F9 listener."""
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
        self._set_idle_status()
        self._input.setText(text)
        self._on_send()

    def _on_voice_status(self, msg: str) -> None:
        self._voice_status.setText(msg)
        self._voice_status.setStyleSheet("color: #888; font-size: 11px; padding: 0 2px;")
        QTimer.singleShot(4000, self._set_idle_status)

    # ── wake word listener ────────────────────────────────────────────────────

    def start_wake_word_listener(self) -> None:
        """Start WakeWordListener if wake word is enabled in settings."""
        from jarvis_app import config
        if not config.wake_word_enabled():
            return
        from jarvis_app.wake_word import WakeWordListener
        self._wwl = WakeWordListener()
        self._wwl.wake_word_detected.connect(self._on_wake_word_detected)
        self._wwl.status_message.connect(self._on_wake_status)
        self._wwl.start()

    def _on_wake_status(self, msg: str) -> None:
        self._voice_status.setText(msg)
        if "aktiv" in msg:
            self._voice_status.setStyleSheet("color: #4ecca3; font-size: 11px; padding: 0 2px;")
            self._mic_btn.setStyleSheet(_MIC_WAKEWORD_STYLE)
        else:
            self._voice_status.setStyleSheet("color: #888; font-size: 11px; padding: 0 2px;")

    def _on_wake_word_detected(self) -> None:
        """Wake word fired — pause listener, start auto-record."""
        if self._wwl:
            self._wwl.pause()

        self._mic_btn.setStyleSheet(_MIC_ACTIVE_STYLE)
        self._voice_status.setText("🟡 'Hey Jarvis' erkannt — spreche deinen Befehl…")
        self._voice_status.setStyleSheet("color: #ffa500; font-size: 11px; padding: 0 2px;")

        self._auto = _WakeAutoThread()
        self._auto.transcription_ready.connect(self._on_voice_text)
        self._auto.status_message.connect(self._on_wake_auto_status)
        self._auto.start()

    def _on_wake_auto_status(self, msg: str) -> None:
        self._voice_status.setText(msg)
        if "Aufnahme" in msg:
            self._voice_status.setStyleSheet("color: #e05555; font-size: 11px; padding: 0 2px;")
            self._mic_btn.setStyleSheet(_MIC_ACTIVE_STYLE)
        else:
            self._voice_status.setStyleSheet("color: #888; font-size: 11px; padding: 0 2px;")
            self._mic_btn.setStyleSheet(_MIC_IDLE_STYLE)
            if "Kein" in msg:
                # Recording failed — resume listener
                QTimer.singleShot(1000, self._resume_wake_word)

    def _resume_wake_word(self) -> None:
        if self._wwl and self._wwl.isRunning():
            self._wwl.resume()
        self._set_idle_status()

    # ── message handling ──────────────────────────────────────────────────────

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text or (self._worker and self._worker.isRunning()):
            return
        self._input.clear()
        self._tabs.setCurrentIndex(1)
        self._chat.add_user(text)
        self._chat.show_typing()
        self._start_thinking_anim()
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
        self._stop_thinking_anim()
        self._chat.hide_typing()
        self._chat.add_jarvis(answer)
        # Resume wake word listener after response; 2 s delay avoids echo triggers
        QTimer.singleShot(2000, self._resume_wake_word)

    # ── thinking animation ────────────────────────────────────────────────────

    def _start_thinking_anim(self) -> None:
        self._pulse_state = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start(600)

    def _stop_thinking_anim(self) -> None:
        if self._pulse_timer:
            self._pulse_timer.stop()
            self._pulse_timer = None
        self._set_idle_status()

    def _pulse_tick(self) -> None:
        self._pulse_state = not self._pulse_state
        if self._pulse_state:
            self._mic_btn.setStyleSheet(_MIC_THINKING_A_STYLE)
            self._voice_status.setText("⏳ Jarvis denkt…")
        else:
            self._mic_btn.setStyleSheet(_MIC_THINKING_B_STYLE)

    def _on_confirm(self, description: str) -> None:
        from jarvis_app.safety.confirmation import ConfirmationDialog
        dialog = ConfirmationDialog(description, parent=self)
        dialog.exec()
        if self._worker:
            self._worker.set_confirmed(dialog.confirmed)

    # ── settings ─────────────────────────────────────────────────────────────

    def _show_settings(self) -> None:
        from jarvis_app.ui.settings_panel import SettingsDialog
        dlg = SettingsDialog(parent=self)
        dlg.exec()
        self._apply_settings()

    def _apply_settings(self) -> None:
        from jarvis_app import config
        enabled    = config.wake_word_enabled()
        wwl_active = bool(self._wwl and self._wwl.isRunning())

        if enabled and not wwl_active:
            self.start_wake_word_listener()
        elif not enabled and wwl_active:
            self._wwl.stop_listening()
            self._wwl.wait(3000)
            self._wwl = None
        self._set_idle_status()

    # ── debug panel ───────────────────────────────────────────────────────────

    def _show_debug_panel(self) -> None:
        from jarvis_app.ui.debug_panel import DebugPanel
        DebugPanel(parent=self).exec()

    # ── startup self-test ─────────────────────────────────────────────────────

    def start_self_test(self) -> None:
        """Run startup check 2 s after launch; auto-open debug panel if errors found."""
        QTimer.singleShot(2000, self._run_self_test)

    def _run_self_test(self) -> None:
        from jarvis_app.startup_check import run_startup_checks, has_errors, summary
        results = run_startup_checks()
        msg = summary(results)
        if has_errors(results):
            self._voice_status.setText(f"🔴 {msg}")
            self._voice_status.setStyleSheet("color: #e05555; font-size: 11px; padding: 0 2px;")
            # Auto-open debug panel so the user can see what's wrong
            self._show_debug_panel()
        else:
            self._voice_status.setText(f"✓ {msg}")
            self._voice_status.setStyleSheet("color: #4ecca3; font-size: 11px; padding: 0 2px;")
            QTimer.singleShot(5000, self._set_idle_status)

    # ── permission center ─────────────────────────────────────────────────────

    def _show_permission_center(self) -> None:
        from jarvis_app.ui.permission_center import PermissionCenter
        dlg = PermissionCenter(parent=self)
        dlg.exec()

    # ── shared helpers ────────────────────────────────────────────────────────

    def _set_idle_status(self) -> None:
        from jarvis_app import config
        if config.wake_word_enabled() and self._wwl and self._wwl.isRunning():
            self._voice_status.setText("🟢 Wake Word aktiv — sage 'Hey Jarvis'")
            self._voice_status.setStyleSheet("color: #4ecca3; font-size: 11px; padding: 0 2px;")
            self._mic_btn.setStyleSheet(_MIC_WAKEWORD_STYLE)
        else:
            self._voice_status.setText("F9 halten zum Sprechen")
            self._voice_status.setStyleSheet("color: #555; font-size: 11px; padding: 0 2px;")
            self._mic_btn.setStyleSheet(_MIC_IDLE_STYLE)

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

_MIC_WAKEWORD_STYLE = (
    "QPushButton { background: #001a0d; border: 1px solid #4ecca3; "
    "border-radius: 8px; font-size: 16px; }"
)

_MIC_THINKING_A_STYLE = (
    "QPushButton { background: #0d1a2e; border: 2px solid #4ecca3; "
    "border-radius: 8px; font-size: 16px; }"
)

_MIC_THINKING_B_STYLE = (
    "QPushButton { background: #1a2e40; border: 1px solid #2a7a6a; "
    "border-radius: 8px; font-size: 16px; }"
)
