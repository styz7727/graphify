from __future__ import annotations
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel


class DiagnosticsSkill(BaseSkill):
    name = "diagnostics"
    description = "Jarvis-Selbstprüfung: Pakete, Logs, Fehler analysieren"
    keywords = ["warum funktioniert jarvis nicht", "jarvis diagnose",
                "selbstprüfung", "fehler analysieren", "was ist kaputt"]
    safety_level = SafetyLevel.SAFE
    examples = ["Warum funktioniert Jarvis nicht?", "Jarvis Diagnose"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        from jarvis_app.diagnostics import run_check
        report = run_check()
        return SkillResult(success=True, message=report)
