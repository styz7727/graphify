"""Check whether a local Ollama server is reachable."""
from __future__ import annotations

import socket
import urllib.request
import json


_HOST = "127.0.0.1"
_PORT = 11434
_TIMEOUT = 1.5


def is_available() -> bool:
    """Return True if Ollama is listening on port 11434."""
    try:
        with socket.create_connection((_HOST, _PORT), timeout=_TIMEOUT):
            return True
    except OSError:
        return False


def get_models() -> list[str]:
    """Return list of model names from Ollama's /api/tags endpoint."""
    try:
        url = f"http://{_HOST}:{_PORT}/api/tags"
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def get_first_model() -> str | None:
    """Return the first available Ollama model, or None."""
    models = get_models()
    return models[0] if models else None


def status_text() -> str:
    """Human-readable status for display in debug panel."""
    if not is_available():
        return "Ollama: nicht erreichbar (localhost:11434)"
    models = get_models()
    if not models:
        return "Ollama: läuft, aber kein Modell geladen (ollama pull mistral)"
    return f"Ollama: läuft — {len(models)} Modell(e): {', '.join(models[:3])}"
