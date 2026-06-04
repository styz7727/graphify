"""Build an ordered list of Steps from an IntentResult."""
from __future__ import annotations

from dataclasses import dataclass

from jarvis_app.brain.intent_router import IntentResult
from jarvis_app.safety.permissions import SafetyLevel, check, describe


@dataclass
class Step:
    intent: str
    entities: dict
    safety_level: SafetyLevel
    description: str        # Human-readable for confirmation dialog


def build_plan(intent: IntentResult) -> list[Step]:
    """Map one IntentResult to one or more executable Steps."""
    if intent.intent == "blocked":
        return [Step(
            intent="blocked",
            entities=intent.entities,
            safety_level=SafetyLevel.BLOCKED,
            description="Blockierte Eingabe"
        )]

    level = check(intent.intent)
    desc = describe(intent.intent, intent.entities)

    return [Step(
        intent=intent.intent,
        entities=intent.entities,
        safety_level=level,
        description=desc,
    )]
