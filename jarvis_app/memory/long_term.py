"""Persistent notes and user preferences (SQLite)."""
from __future__ import annotations

from jarvis_app.memory.storage import db


# ── Notes ─────────────────────────────────────────────────────────────────────

def save_note(content: str, tags: str = "") -> int:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO notes (content, tags) VALUES (?, ?)", (content, tags)
        )
        return cur.lastrowid


def get_notes(limit: int = 20) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, content, created, tags FROM notes ORDER BY created DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_note(note_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))


# ── Preferences ───────────────────────────────────────────────────────────────

def get_pref(key: str, default: str = "") -> str:
    with db() as conn:
        row = conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_pref(key: str, value: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO preferences (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
