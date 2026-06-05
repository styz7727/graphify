"""In-memory conversation context for the current session."""
from __future__ import annotations

_MAX_TURNS = 10
_session: list[dict] = []
_pending: dict | None = None   # pending clarification {"intent": str, "entities": dict}


class ShortTerm:
    """Thin wrapper around the module-level session list (singleton per process)."""

    def context(self) -> list[dict]:
        return list(_session)

    def add(self, user: str, jarvis: str) -> None:
        _session.append({"user": user, "jarvis": jarvis})
        if len(_session) > _MAX_TURNS:
            _session.pop(0)

    def clear(self) -> None:
        _session.clear()

    def last_user_message(self) -> str:
        return _session[-1]["user"] if _session else ""

    # ── pending clarification ─────────────────────────────────────────────────

    def set_pending(self, intent: str, entities: dict, question: str = "") -> None:
        global _pending
        _pending = {"intent": intent, "entities": entities, "question": question}

    def get_pending(self) -> dict | None:
        return _pending

    def clear_pending(self) -> None:
        global _pending
        _pending = None
