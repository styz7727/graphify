"""ResponseWorker — runs the full brain pipeline in a background QThread."""
from __future__ import annotations

import threading

from PyQt6.QtCore import QThread, pyqtSignal as Signal


class ResponseWorker(QThread):
    """Processes one user message through: intent → plan → safety → execute → reflect."""

    response_ready = Signal(str, str)   # (question, answer)
    needs_confirmation = Signal(str)    # human-readable action description

    def __init__(self, question: str) -> None:
        super().__init__()
        self._question = question
        self._confirm_event = threading.Event()
        self._confirmed = False

    # ── called from main thread ────────────────────────────────────────────────

    def set_confirmed(self, confirmed: bool) -> None:
        self._confirmed = confirmed
        self._confirm_event.set()

    # ── internal confirmation helper (blocks worker thread) ───────────────────

    def _request_confirmation(self, description: str) -> bool:
        self._confirm_event.clear()
        self.needs_confirmation.emit(description)
        fired = self._confirm_event.wait(timeout=60)
        return fired and self._confirmed

    # ── QThread.run ───────────────────────────────────────────────────────────

    def run(self) -> None:
        from jarvis_app.brain.intent_router import route
        from jarvis_app.brain.planner import build_plan
        from jarvis_app.brain.executor import execute
        from jarvis_app.brain.reflection import build_response
        from jarvis_app.memory.short_term import ShortTerm
        from jarvis_app.memory.episodic import log_action
        from jarvis_app import voice

        st = ShortTerm()
        try:
            intent = route(self._question, st.context())
            steps = build_plan(intent)
            results = execute(steps, self._request_confirmation)
            answer = build_response(self._question, intent, results)
            st.add(self._question, answer)
            log_action(intent.intent, self._question, "completed")
        except Exception as exc:
            answer = f"Fehler: {exc}"
            log_action("unknown", self._question, f"error: {exc}")

        self.response_ready.emit(self._question, answer)
        voice.speak(answer)
