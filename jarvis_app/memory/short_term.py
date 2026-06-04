"""In-memory conversation context for the current session."""
from __future__ import annotations

_MAX_TURNS = 10
_session: list[dict] = []


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
