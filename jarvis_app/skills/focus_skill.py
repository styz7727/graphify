from __future__ import annotations
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel


class FocusSkill(BaseSkill):
    name = "focus_mode"
    description = "Arbeits-, Lern- oder Tradingmodus starten"
    keywords = ["arbeitsmodus", "lernmodus", "tradingmodus", "schulmodus",
                "starte arbeitsmodus", "starte lernmodus", "starte tradingmodus"]
    safety_level = SafetyLevel.CONFIRM
    examples = ["Starte Arbeitsmodus", "Lernmodus starten", "Starte Tradingmodus"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        from jarvis_app.modes import MODES
        mode = entities.get("mode", "work")
        cfg = MODES.get(mode)
        if not cfg:
            available = ", ".join(MODES.keys())
            return SkillResult(success=False, message=f"Unbekannter Modus. Verfügbar: {available}")

        from jarvis_app.tools.app_launcher import launch
        from jarvis_app.tools.browser_tools import open_url

        results = []
        for app in cfg.get("apps", []):
            results.append(launch(app))
        for url in cfg.get("urls", []):
            open_url(url)

        name = cfg.get("name", mode)
        return SkillResult(
            success=True,
            message=f"{name} gestartet. {cfg.get('message', '')}",
            data={"mode": mode}
        )
