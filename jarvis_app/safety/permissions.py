"""SAFE / CONFIRM / BLOCKED classification for every intent."""
from __future__ import annotations

from enum import Enum


class SafetyLevel(Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    BLOCKED = "blocked"


_LEVELS: dict[str, SafetyLevel] = {
    # ── SAFE — execute immediately ────────────────────────────────────────────
    "weather":          SafetyLevel.SAFE,
    "notes_save":       SafetyLevel.SAFE,
    "notes_read":       SafetyLevel.SAFE,
    "reminders_set":    SafetyLevel.SAFE,
    "reminders_read":   SafetyLevel.SAFE,
    "git_summary":      SafetyLevel.SAFE,
    "knowledge_query":  SafetyLevel.SAFE,
    "diagnostics":      SafetyLevel.SAFE,
    "help":             SafetyLevel.SAFE,
    "unknown":          SafetyLevel.SAFE,
    "memory_save":      SafetyLevel.SAFE,
    "memory_read":      SafetyLevel.SAFE,
    "self_improve":     SafetyLevel.SAFE,

    # ── CONFIRM — requires user approval ─────────────────────────────────────
    "open_app":         SafetyLevel.CONFIRM,
    "browser_open":     SafetyLevel.CONFIRM,
    "web_search":       SafetyLevel.CONFIRM,
    "tradingview":      SafetyLevel.CONFIRM,
    "focus_mode":       SafetyLevel.CONFIRM,
    "calendar_prep":    SafetyLevel.CONFIRM,
    "memory_delete":    SafetyLevel.CONFIRM,

    # ── BLOCKED — permanent refusal ───────────────────────────────────────────
    "shell_exec":       SafetyLevel.BLOCKED,
    "read_secrets":     SafetyLevel.BLOCKED,
    "send_message":     SafetyLevel.BLOCKED,
    "delete_file":      SafetyLevel.BLOCKED,
    "install":          SafetyLevel.BLOCKED,
}

# Substrings that trigger BLOCKED regardless of classified intent
_BLOCKED_INPUT_PATTERNS = [
    "api_key", "api-key", "apikey",
    "password", "passwort", "kennwort",
    "token", "secret", "credentials", "credential",
    "private_key", "privatekey",
    "rm -rf", "del /f", "format c:", "shutdown", "taskkill",
    "pip install", "npm install", "winget install",
    ".env", "~/.ssh", "~/.aws",
]


def check(intent: str) -> SafetyLevel:
    return _LEVELS.get(intent.lower(), SafetyLevel.SAFE)


def is_blocked_input(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in _BLOCKED_INPUT_PATTERNS)


def describe(intent: str, entities: dict) -> str:
    """Human-readable description for confirmation dialogs."""
    target = entities.get("target") or entities.get("query") or entities.get("symbol") or ""
    content = entities.get("content", "")
    scope   = entities.get("scope", "last")
    descriptions = {
        "open_app":      f"Programm öffnen: {target}",
        "browser_open":  f"Webseite öffnen: {target}",
        "web_search":    f"Im Internet suchen: {target}",
        "tradingview":   f"TradingView öffnen: {target}",
        "focus_mode":    f"Modus starten: {target}",
        "calendar_prep": f"Termin vorbereiten: {target}",
        "memory_delete": (
            "Alle persönlichen Einträge löschen"
            if scope == "all"
            else f"Letzten Eintrag löschen: '{content}'"
        ),
    }
    return descriptions.get(intent, f"{intent}: {target}")
