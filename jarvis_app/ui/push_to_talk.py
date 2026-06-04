"""F9 global Push-to-talk listener. Runs pynput in a QThread, emits Qt signals."""
from __future__ import annotations

import threading

from PyQt6.QtCore import QThread, pyqtSignal as Signal


class PushToTalkWorker(QThread):
    """Global F9 listener: press = record, release = transcribe + emit text."""

    recording_started  = Signal()        # F9 pressed, mic open
    recording_stopped  = Signal()        # F9 released, transcribing
    transcription_ready = Signal(str)    # final text, ready to send
    status_message     = Signal(str)     # human-readable status for UI

    def __init__(self) -> None:
        super().__init__()
        self._recording = False
        self._stop_event: threading.Event | None = None

    # ── QThread ───────────────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            from pynput import keyboard
        except ImportError:
            self.status_message.emit("pynput fehlt — F9 nicht verfügbar")
            return

        def on_press(key):
            if key == keyboard.Key.f9 and not self._recording:
                self._recording = True
                self._stop_event = threading.Event()
                self.recording_started.emit()
                t = threading.Thread(
                    target=self._capture_and_transcribe,
                    args=(self._stop_event,),
                    daemon=True,
                )
                t.start()

        def on_release(key):
            if key == keyboard.Key.f9 and self._recording:
                self._recording = False
                self.recording_stopped.emit()
                if self._stop_event:
                    self._stop_event.set()

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    # ── worker ────────────────────────────────────────────────────────────────

    def _capture_and_transcribe(self, stop_event: threading.Event) -> None:
        from jarvis_app import voice
        import numpy as np

        audio = voice.record_audio(stop_event)
        if audio is None:
            self.status_message.emit("Mikrofon nicht verfügbar")
            return

        # Ignore very short presses (< 300 ms at 16 kHz)
        if len(audio) < voice._SAMPLE_RATE * 0.3:
            self.status_message.emit("Aufnahme zu kurz")
            return

        self.status_message.emit("⏳ Transkribiere…")
        text = voice.transcribe(audio)
        if text:
            self.transcription_ready.emit(text)
        else:
            self.status_message.emit("Kein Text erkannt — nochmal versuchen")
