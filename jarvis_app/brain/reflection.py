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
        # Disambiguation: check if we should ask a clarifying question
        clarification = _check_clarification(question, intent)
        if clarification:
            return clarification
        return "Ich habe keine Aktion ausgeführt."

    parts: list[str] = []
    for r in results:
        if r.decision == "blocked":
            parts.append(
                "Das kann ich aus Sicherheitsgründen nicht tun.\n"
                "Erlaubte Aktionen: Notizen, Wetter, Apps öffnen (mit Bestätigung), Fragen beantworten."
            )
        elif r.decision == "cancelled":
            parts.append("Abgebrochen. Sag mir Bescheid wenn du es doch möchtest.")
        elif r.skill_result:
            parts.append(r.skill_result.message)
        else:
            parts.append("Fertig.")

    response = " ".join(parts)
    return clean(response)


def _check_clarification(question: str, intent: IntentResult) -> str | None:
    """Return a clarifying question if the intent seems ambiguous."""
    q = question.lower().strip()
    # Simple affirmative without context
    if q in ("ja", "nein", "ok", "okay", "ja.", "nein."):
        return "Worauf beziehst du dich? Ich konnte keinen offenen Kontext finden."
    # Very short or unclear message
    if len(q) <= 3 and q not in ("ja", "ok"):
        return "Kannst du das etwas genauer erklären?"
    return None
