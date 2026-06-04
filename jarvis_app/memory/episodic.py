"""Daily JSONL action log for episodic memory — what Jarvis did today."""
from __future__ import annotations

import json
from datetime import datetime, date, timezone
from pathlib import Path

from jarvis_app import config


def _today_log() -> Path:
    return config.LOG_DIR / f"episode_{date.today().isoformat()}.jsonl"


def log_action(intent: str, text: str, result: str) -> None:
    entry = {
        "ts":     datetime.now(timezone.utc).isoformat(),
        "intent": intent,
        "text":   text[:200],
        "result": result[:200],
    }
    try:
        with open(_today_log(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def today_summary() -> list[dict]:
    """Return today's logged actions."""
    try:
        lines = _today_log().read_text(encoding="utf-8").splitlines()
        return [json.loads(l) for l in lines if l.strip()]
    except Exception:
        return []
