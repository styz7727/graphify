"""Abstract base class for all Jarvis skills."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from jarvis_app.safety.permissions import SafetyLevel


@dataclass
class SkillResult:
    success: bool
    message: str                   # German response for the user
    data: dict = field(default_factory=dict)  # extra payload (dashboard, etc.)


class BaseSkill(ABC):
    name: str = ""
    description: str = ""
    keywords: list[str] = []
    safety_level: SafetyLevel = SafetyLevel.SAFE
    examples: list[str] = []

    @abstractmethod
    def handle(self, intent: str, entities: dict) -> SkillResult:
        """Execute the skill and return a result."""

    def matches(self, text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in self.keywords)
