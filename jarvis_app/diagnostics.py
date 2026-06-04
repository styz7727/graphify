"""Self-check: required packages, config, recent errors."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from jarvis_app import config

_REQUIRED = {
    "PyQt6":       "PyQt6",
    "edge_tts":    "edge-tts",
    "requests":    "requests",
}
_OPTIONAL = {
    "anthropic":   "anthropic",
    "faster_whisper": "faster-whisper (für Spracheingabe, v2)",
}


def run_check() -> str:
    lines: list[str] = ["=== Jarvis Diagnose ===", ""]

    # Package check
    lines.append("Pakete:")
    ok = True
    for mod, pkg in _REQUIRED.items():
        found = importlib.util.find_spec(mod) is not None
        lines.append(f"  {'✓' if found else '✗'} {pkg}")
        if not found:
            ok = False
    lines.append("Optional:")
    for mod, pkg in _OPTIONAL.items():
        found = importlib.util.find_spec(mod) is not None
        lines.append(f"  {'✓' if found else '○'} {pkg}")

    # Config
    lines.append("")
    lines.append("Konfiguration:")
    lines.append(f"  App-Verzeichnis: {config.APP_DIR}")
    lines.append(f"  Datenbank: {'✓' if config.DB_PATH.exists() else '✗ fehlt'}")
    lines.append(f"  Graph: {'✓' if config.graph_path().exists() else '✗ nicht gefunden'}")
    lines.append(f"  LLM-Backend: {config.llm_backend()}")

    # LLM reachable?
    try:
        from graphify.llm import detect_backend
        backend = detect_backend()
        lines.append(f"  LLM erreichbar: {'✓ ' + backend if backend else '✗ kein API-Key gesetzt'}")
    except Exception as e:
        lines.append(f"  LLM-Check Fehler: {e}")

    # Recent errors
    lines.append("")
    lines.append("Letzte Fehler im Action-Log:")
    from jarvis_app.safety.action_log import recent
    errors = [e for e in recent(50) if "error" in e.get("result", "").lower()][-5:]
    if errors:
        for e in errors:
            lines.append(f"  ✗ [{e.get('ts','')[:16]}] {e.get('intent','')}: {e.get('result','')}")
    else:
        lines.append("  Keine Fehler.")

    if ok:
        lines.append("")
        lines.append("✓ Alle Pflichtpakete vorhanden.")
    else:
        lines.append("")
        lines.append("→ Führe aus: uv sync --extra jarvis-app")

    return "\n".join(lines)
