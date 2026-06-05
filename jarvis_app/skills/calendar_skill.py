"""Calendar skill — v1 prepares appointments only, never auto-enters them. (Full impl: v3)"""
from __future__ import annotations
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel


class CalendarSkill(BaseSkill):
    name = "calendar_prep"
    description = "Termine vorbereiten (niemals automatisch eintragen)"
    keywords = ["termin", "kalender", "was steht heute an", "meeting", "appointment"]
    safety_level = SafetyLevel.CONFIRM
    examples = ["Termin mit Lukas am Freitag um 15 Uhr", "Was steht heute an?"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        content = entities.get("content", "")
        if not content:
            from jarvis_app.memory.reminders import get_today
            today = get_today()
            if not today:
                return SkillResult(success=True, message="Heute keine Termine in Jarvis.")
            lines = [f"• {r['content']} ({r['due_text']})" for r in today]
            return SkillResult(success=True, message="Heutige Erinnerungen:\n" + "\n".join(lines))

        # Prepare-only: show structured preview, copy to clipboard
        preview = f"Termin: {content}"
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-c", f'Set-Clipboard "{content}"'],
                capture_output=True, timeout=5
            )
            return SkillResult(
                success=True,
                message=f"Termin vorbereitet und in Zwischenablage kopiert: {content}\n"
                        "Du kannst ihn jetzt im Kalender einfügen."
            )
        except Exception:
            return SkillResult(success=True, message=f"Termin vorbereitet: {content}")
