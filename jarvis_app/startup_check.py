"""Startup self-test — checks every required component before the app is usable."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Literal

Status = Literal["ok", "warn", "error"]


@dataclass
class CheckResult:
    name:    str
    status:  Status
    message: str


# ── public API ────────────────────────────────────────────────────────────────

def run_startup_checks() -> list[CheckResult]:
    results: list[CheckResult] = []
    _check_python(results)
    _check_microphone(results)
    _check_whisper(results)
    _check_tts(results)
    _check_wake_word(results)
    _check_api_keys(results)
    _check_f9(results)
    _check_app_dir(results)
    return results


def has_errors(results: list[CheckResult]) -> bool:
    return any(r.status == "error" for r in results)


def has_warnings(results: list[CheckResult]) -> bool:
    return any(r.status == "warn" for r in results)


def summary(results: list[CheckResult]) -> str:
    errors = sum(1 for r in results if r.status == "error")
    warns  = sum(1 for r in results if r.status == "warn")
    ok     = sum(1 for r in results if r.status == "ok")
    if errors:
        return f"{errors} Fehler, {warns} Warnungen — Debug-Panel öffnen"
    if warns:
        return f"Bereit mit {warns} Hinweis(en)"
    return f"Alle {ok} Checks OK — Jarvis bereit"


# ── individual checks ─────────────────────────────────────────────────────────

def _check_python(out: list) -> None:
    v = sys.version_info
    s = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 11):
        out.append(CheckResult("Python", "ok", s))
    else:
        out.append(CheckResult("Python", "warn", f"{s} — 3.11+ empfohlen für faster-whisper"))


def _check_microphone(out: list) -> None:
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        n_in = sum(1 for d in devices if d["max_input_channels"] > 0)
        if n_in:
            out.append(CheckResult("Mikrofon", "ok", f"{n_in} Eingabegerät(e) gefunden"))
        else:
            out.append(CheckResult("Mikrofon", "warn", "Kein Mikrofon — Spracheingabe nicht möglich"))
    except ImportError:
        out.append(CheckResult("Mikrofon", "error", "sounddevice fehlt → uv sync --extra jarvis-app"))
    except Exception as exc:
        out.append(CheckResult("Mikrofon", "warn", f"Abfrage fehlgeschlagen: {exc}"))


def _check_whisper(out: list) -> None:
    try:
        from faster_whisper import WhisperModel  # noqa: F401
        out.append(CheckResult("STT (Whisper)", "ok", "faster-whisper installiert"))
    except ImportError:
        out.append(CheckResult("STT (Whisper)", "error",
                               "faster-whisper fehlt — Spracherkennung deaktiviert"))


def _check_tts(out: list) -> None:
    try:
        import edge_tts  # noqa: F401
        out.append(CheckResult("TTS (edge-tts)", "ok", "verfügbar"))
    except ImportError:
        out.append(CheckResult("TTS (edge-tts)", "error",
                               "edge-tts fehlt — Sprachausgabe deaktiviert"))


def _check_wake_word(out: list) -> None:
    try:
        import openwakeword  # noqa: F401
        out.append(CheckResult("Wake Word", "ok", "openwakeword verfügbar"))
    except ImportError:
        out.append(CheckResult("Wake Word", "warn",
                               "openwakeword fehlt — Wake Word deaktiviert"))


def _check_api_keys(out: list) -> None:
    """Check for any LLM API key. Never log or display the actual value."""
    for env_var, label in [
        ("ANTHROPIC_API_KEY", "Anthropic"),
        ("OPENAI_API_KEY",    "OpenAI"),
        ("GEMINI_API_KEY",    "Gemini"),
        ("GOOGLE_API_KEY",    "Google"),
    ]:
        key = os.environ.get(env_var, "")
        if key and len(key) > 8:
            masked = f"...{key[-4:]}"
            out.append(CheckResult(
                f"API Key ({label})", "ok",
                f"Gesetzt ({masked}, Länge {len(key)})"
            ))
            return   # one valid key is enough

    out.append(CheckResult(
        "API Key", "warn",
        "Kein API-Key gesetzt — LLM-Abfragen nicht verfügbar. "
        "Setze ANTHROPIC_API_KEY in der Shell vor dem Start."
    ))


def _check_f9(out: list) -> None:
    try:
        import pynput  # noqa: F401
        out.append(CheckResult("F9 Push-to-talk", "ok", "pynput installiert"))
    except ImportError:
        out.append(CheckResult("F9 Push-to-talk", "error",
                               "pynput fehlt — F9 nicht verfügbar"))


def _check_app_dir(out: list) -> None:
    from jarvis_app import config
    issues = []
    if not config.APP_DIR.exists():
        issues.append("App-Verzeichnis fehlt")
    if not config.DB_PATH.exists():
        issues.append("Datenbank fehlt (wird beim ersten Start angelegt)")
    if issues:
        out.append(CheckResult("App-Verzeichnis", "warn", "; ".join(issues)))
    else:
        out.append(CheckResult("App-Verzeichnis", "ok", str(config.APP_DIR)))
