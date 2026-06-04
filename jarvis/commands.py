"""Route transcribed speech to the right action."""
from __future__ import annotations

import subprocess

from jarvis.knowledge import Knowledge

_KEYWORDS: dict[str, list[str]] = {
    "tests":        ["tests laufen", "tests ausführen", "pytest", "test starten", "run tests"],
    "god_nodes":    ["god nodes", "zentrale module", "wichtigste knoten", "god node", "godnode"],
    "architecture": ["architektur", "projektstruktur", "aufbau", "überblick", "wie ist das projekt aufgebaut"],
    "help":         ["hilfe", "befehle", "was kannst du", "help", "was weißt du"],
}


def _matches(text: str, keys: list[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keys)


def route(text: str, knowledge: Knowledge) -> str:
    if _matches(text, _KEYWORDS["tests"]):
        return _run_tests()
    if _matches(text, _KEYWORDS["god_nodes"]):
        nodes = knowledge.god_nodes()
        return "Die zentralsten Knoten sind: " + ", ".join(nodes) + "."
    if _matches(text, _KEYWORDS["architecture"]):
        return knowledge.summary()
    if _matches(text, _KEYWORDS["help"]):
        return (
            "Du kannst sagen: Tests laufen lassen, God Nodes zeigen, "
            "Architektur erklären — oder einfach eine Frage zum Code stellen."
        )
    return knowledge.ask(text)


def _run_tests() -> str:
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return "uv nicht gefunden. Stelle sicher dass uv installiert ist."
    except subprocess.TimeoutExpired:
        return "Tests haben das Zeitlimit überschritten."

    lines = [l for l in (result.stdout + result.stderr).splitlines() if l.strip()]
    summary = lines[-1] if lines else "Keine Ausgabe."
    ok = result.returncode == 0
    return f"Tests {'bestanden' if ok else 'fehlgeschlagen'}: {summary}"
