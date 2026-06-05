from __future__ import annotations
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel
from jarvis_app.memory import long_term, reminders


class NotesSkill(BaseSkill):
    name = "notes"
    description = "Notizen speichern/lesen und Erinnerungen setzen"
    keywords = ["notiere", "notiere dir", "schreib auf", "merke dir",
                "was habe ich notiert", "meine notizen",
                "erinnere mich", "erinnerung", "was steht heute an"]
    safety_level = SafetyLevel.SAFE
    examples = ["Notiere dir: Meeting um 15 Uhr", "Was habe ich notiert?",
                "Erinnere mich an den Arzttermin", "Was steht heute an?"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        if intent == "notes_save":
            content = entities.get("content", "")
            if not content:
                return SkillResult(success=False, message="Was soll ich notieren?")
            long_term.save_note(content)
            return SkillResult(success=True, message=f"Notiert: {content}")

        if intent == "notes_read":
            notes = long_term.get_notes(10)
            if not notes:
                return SkillResult(success=True, message="Keine Notizen vorhanden.")
            lines = [f"• {n['content']}" for n in notes]
            return SkillResult(success=True, message="Meine Notizen:\n" + "\n".join(lines))

        if intent == "reminders_set":
            content = entities.get("content", "")
            due = entities.get("due", "unbekannte Zeit")
            if not content:
                return SkillResult(success=False, message="Was soll ich dir erinnern?")
            reminders.save_reminder(content, due)
            return SkillResult(success=True, message=f"Erinnerung gespeichert: {content} — {due}")

        if intent == "reminders_read":
            today = reminders.get_today()
            if not today:
                return SkillResult(success=True, message="Heute keine Erinnerungen.")
            lines = [f"• {r['content']} ({r['due_text']})" for r in today]
            return SkillResult(success=True, message="Heute:\n" + "\n".join(lines))

        return SkillResult(success=False, message="Unbekannter Notiz-Befehl.")
