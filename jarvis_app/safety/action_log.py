"""Append-only JSONL action log — every action is recorded."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from jarvis_app import config


def log(
    intent: str,
    target: str,
    safety_level: str,
    decision: str,
    result: str = "",
) -> None:
    entry = {
        "ts":           datetime.now(timezone.utc).isoformat(),
        "intent":       intent,
        "target":       _truncate(target),
        "safety_level": safety_level,
        "decision":     decision,
        "result":       _truncate(result),
    }
    try:
        with open(config.ACTION_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[ActionLog] Fehler beim Schreiben: {e}")


def recent(n: int = 20) -> list[dict]:
    """Return the last n log entries."""
    try:
        lines = config.ACTION_LOG_PATH.read_text(encoding="utf-8").splitlines()
        return [json.loads(l) for l in lines[-n:] if l.strip()]
    except Exception:
        return []


def _truncate(s: str, limit: int = 200) -> str:
    return s[:limit] + "…" if len(s) > limit else s
