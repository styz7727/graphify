"""Build a natural German response from execution results."""
from __future__ import annotations

from jarvis_app.brain.intent_router import IntentResult
from jarvis_app.brain.executor import ExecutionResult
from jarvis_app.safety.redaction import clean


def build_response(
    question: str,
    intent: IntentResult,
    results: list[ExecutionResult],
) -> str:
    if not results:
        return "Ich habe keine Aktion ausgeführt."

    parts: list[str] = []
    for r in results:
        if r.decision == "blocked":
            parts.append("Das kann ich aus Sicherheitsgründen nicht tun.")
        elif r.decision == "cancelled":
            parts.append("Abgebrochen.")
        elif r.skill_result:
            parts.append(r.skill_result.message)
        else:
            parts.append("Fertig.")

    response = " ".join(parts)
    return clean(response)  # strip any secrets that slipped through
