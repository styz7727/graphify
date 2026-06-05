from __future__ import annotations
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel
from jarvis_app.tools.app_launcher import launch, available_apps


class AppLauncherSkill(BaseSkill):
    name = "open_app"
    description = "Whitelisted Programme öffnen"
    keywords = ["öffne ", "starte ", "launch "]
    safety_level = SafetyLevel.CONFIRM
    examples = ["Öffne Teams", "Starte Chrome", "Öffne Explorer"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        app = entities.get("target", "")
        if not app:
            apps = ", ".join(available_apps())
            return SkillResult(success=False, message=f"Welches Programm? Verfügbar: {apps}")
        msg = launch(app)
        return SkillResult(success=True, message=msg)
