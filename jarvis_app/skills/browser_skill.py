from __future__ import annotations
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel
from jarvis_app.tools.browser_tools import open_url, web_search


class BrowserSkill(BaseSkill):
    name = "browser"
    description = "Webseiten öffnen oder im Internet suchen"
    keywords = ["suche im internet", "suche nach", "öffne die webseite", "gehe zu", "navigiere zu"]
    safety_level = SafetyLevel.CONFIRM
    examples = ["Suche im Internet nach Python", "Öffne die Webseite example.com"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        if intent == "web_search":
            query = entities.get("query", "")
            if not query:
                return SkillResult(success=False, message="Wonach soll ich suchen?")
            msg = web_search(query)
        else:
            url = entities.get("url", entities.get("target", ""))
            if not url:
                return SkillResult(success=False, message="Welche URL soll ich öffnen?")
            msg = open_url(url)
        return SkillResult(success=True, message=msg)
