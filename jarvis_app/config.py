"""Central configuration — QSettings persistence + runtime defaults."""
from __future__ import annotations

import json
from pathlib import Path

APP_NAME = "Jarvis"
APP_DIR = Path.home() / ".jarvis_app"
LOG_DIR = APP_DIR / "logs"
DB_PATH = APP_DIR / "memory.db"
CHAT_HISTORY_PATH = APP_DIR / "chat_history.json"
ACTION_LOG_PATH = APP_DIR / "action_log.jsonl"

APP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULT_APP_WHITELIST = {
    "teams":    r"%LOCALAPPDATA%\Microsoft\Teams\Update.exe --processStart Teams.exe",
    "chrome":   r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":  r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "explorer": "explorer.exe",
    "notepad":  "notepad.exe",
    "vscode":   "code",
    "code":     "code",
}


def _settings():
    from PyQt6.QtCore import QSettings
    return QSettings(APP_NAME, APP_NAME)


def get(key: str, default=None):
    try:
        return _settings().value(key, default)
    except Exception:
        return default


def set_(key: str, value) -> None:
    try:
        _settings().setValue(key, value)
    except Exception:
        pass


# ── typed accessors ────────────────────────────────────────────────────────────

def llm_backend() -> str:
    return get("llm_backend", "claude")


def tts_voice() -> str:
    return get("tts_voice", "de-DE-ConradNeural")


def city() -> str:
    return get("city", "Zürich")


def graph_path() -> Path:
    return Path(get("graph_path", "graphify-out/graph.json"))


def app_whitelist() -> dict[str, str]:
    raw = get("app_whitelist", None)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return dict(_DEFAULT_APP_WHITELIST)


def tts_enabled() -> bool:
    v = get("tts_enabled", "true")
    return str(v).lower() not in ("false", "0", "no")


def wake_word_enabled() -> bool:
    v = get("wake_word_enabled", "false")
    return str(v).lower() in ("true", "1", "yes")


def set_wake_word_enabled(v: bool) -> None:
    set_("wake_word_enabled", "true" if v else "false")


def wake_word_threshold() -> float:
    try:
        return float(get("wake_word_threshold", "0.5"))
    except (TypeError, ValueError):
        return 0.5


def set_wake_word_threshold(v: float) -> None:
    set_("wake_word_threshold", str(round(float(v), 3)))


def set_tts_voice(voice: str) -> None:
    set_("tts_voice", voice)


def set_city(city_: str) -> None:
    set_("city", city_)
