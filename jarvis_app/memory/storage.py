"""SQLite connection + schema migrations for Jarvis memory."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from jarvis_app import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    content   TEXT    NOT NULL,
    created   TEXT    NOT NULL DEFAULT (datetime('now')),
    tags      TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reminders (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    content   TEXT    NOT NULL,
    due_text  TEXT    NOT NULL,
    done      INTEGER NOT NULL DEFAULT 0,
    created   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS preferences (
    key       TEXT PRIMARY KEY,
    value     TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


ensure_schema()
