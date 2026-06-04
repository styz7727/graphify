"""Reminders stored in SQLite, polled every minute via QTimer."""
from __future__ import annotations

from datetime import date

from jarvis_app.memory.storage import db


def save_reminder(content: str, due_text: str) -> int:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (content, due_text) VALUES (?, ?)",
            (content, due_text)
        )
        return cur.lastrowid


def get_today() -> list[dict]:
    """Return undone reminders that mention today's date or 'heute'."""
    today = date.today().strftime("%d.%m.%Y")
    with db() as conn:
        rows = conn.execute(
            "SELECT id, content, due_text FROM reminders WHERE done = 0 "
            "ORDER BY created DESC"
        ).fetchall()
    results = []
    for r in rows:
        due = r["due_text"].lower()
        if "heute" in due or today in due:
            results.append(dict(r))
    return results


def get_all_pending() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, content, due_text, created FROM reminders "
            "WHERE done = 0 ORDER BY created DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def mark_done(reminder_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
