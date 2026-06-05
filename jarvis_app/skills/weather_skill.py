from __future__ import annotations
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel
from jarvis_app.tools.weather import get_weather


class WeatherSkill(BaseSkill):
    name = "weather"
    description = "Aktuelles Wetter und Vorhersage abfragen"
    keywords = ["wetter", "temperatur", "regen", "wind", "schnee", "wie ist das wetter", "grad"]
    safety_level = SafetyLevel.SAFE
    examples = ["Wie ist das Wetter?", "Wetter in Berlin", "Regnet es heute?"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        city = entities.get("city")
        result = get_weather(city)
        return SkillResult(success=True, message=result, data={"weather": result})
