"""Wake word detection via OpenWakeWord — background QThread.

Privacy guarantee: audio is processed in-memory only.  Nothing is stored
or transmitted.  The thread exits immediately if wake_word_enabled() is False.
"""
from __future__ import annotations

import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal as Signal

_CHUNK  = 1280    # 80 ms at 16 kHz — openwakeword's preferred chunk size
_RATE   = 16_000
_MODELS = ["hey_jarvis_v0.1", "hey_jarvis"]   # candidates, first match wins


class WakeWordListener(QThread):
    """Listen for 'Hey Jarvis' using OpenWakeWord.

    Call pause() while recording a command so the listener doesn't
    trigger again mid-session.  Call resume() when done.
    """

    wake_word_detected = Signal()
    status_message     = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._active     = True
        self._pause_flag = threading.Event()   # set = paused, clear = active

    # ── public control ────────────────────────────────────────────────────────

    def pause(self) -> None:
        self._pause_flag.set()

    def resume(self) -> None:
        self._pause_flag.clear()

    def stop_listening(self) -> None:
        self._active = False
        self._pause_flag.set()   # unblock any sleep

    # ── thread body ───────────────────────────────────────────────────────────

    def run(self) -> None:
        from jarvis_app import config

        if not config.wake_word_enabled():
            return

        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            self.status_message.emit("sounddevice fehlt — Wake Word nicht verfügbar")
            return

        oww = self._load_model()
        if oww is None:
            return

        self.status_message.emit("🟢 Wake Word aktiv — sage 'Hey Jarvis'")
        threshold = config.wake_word_threshold()
        buf: list = []

        def _cb(indata, frames, t, status):
            if not self._pause_flag.is_set():
                buf.append(indata.copy().flatten())

        try:
            with sd.InputStream(
                samplerate=_RATE,
                channels=1,
                dtype="float32",
                blocksize=_CHUNK,
                callback=_cb,
            ):
                while self._active:
                    if self._pause_flag.is_set():
                        buf.clear()
                        time.sleep(0.05)
                        continue

                    if not buf:
                        time.sleep(0.01)
                        continue

                    chunk_i16 = (buf.pop(0) * 32767).astype(np.int16)
                    scores = oww.predict(chunk_i16)
                    if any(s >= threshold for s in scores.values()):
                        oww.reset()
                        buf.clear()
                        self.wake_word_detected.emit()

        except Exception as exc:
            self.status_message.emit(f"Wake-Word-Fehler: {exc}")

    # ── model loading ─────────────────────────────────────────────────────────

    def _load_model(self):
        try:
            from openwakeword.model import Model as _Model
        except ImportError:
            self.status_message.emit(
                "openwakeword fehlt — 'uv sync --extra jarvis-app' ausführen"
            )
            return None

        self.status_message.emit("⏳ Lade Wake-Word-Modell…")

        # Try already-installed / previously-downloaded models first
        for name in _MODELS:
            try:
                return _Model(wakeword_models=[name], inference_framework="onnx")
            except Exception:
                pass

        # One-time download from HuggingFace (openwakeword model hub)
        try:
            self.status_message.emit("⬇️ Lade hey_jarvis Modell herunter (einmalig)…")
            from openwakeword.utils import download_models
            download_models(["hey_jarvis_v0.1"])
            return _Model(wakeword_models=["hey_jarvis_v0.1"], inference_framework="onnx")
        except Exception as exc:
            self.status_message.emit(
                f"hey_jarvis Modell nicht gefunden ({exc}). "
                "Manuell installieren: siehe CLAUDE.md → Wake Word."
            )
            return None
