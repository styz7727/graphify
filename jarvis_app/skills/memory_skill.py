"""Persistent personal memory — save, read, delete personal facts."""
from __future__ import annotations

from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel
from jarvis_app.memory import long_term


class MemorySkill(BaseSkill):
    name = "memory"
    description = "Persönliche Fakten dauerhaft speichern, lesen und löschen"
    keywords = ["merke dir das", "ich heisse", "was weisst du über mich", "vergiss das"]
    safety_level = SafetyLevel.SAFE
    examples = [
        "Merke dir das",
        "Ich heisse Marc",
        "Was weisst du über mich?",
        "Vergiss das",
    ]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        if intent == "memory_save":
            return self._save(entities)
        if intent == "memory_read":
            return self._read()
        if intent == "memory_delete":
            return self._delete(entities)
        return SkillResult(success=False, message="Unbekannter Speicher-Befehl.")

    # ── save ──────────────────────────────────────────────────────────────────

    def _save(self, entities: dict) -> SkillResult:
        content = entities.get("content", "").strip()
        if not content:
            from jarvis_app.memory.short_term import ShortTerm
            last = ShortTerm().last_user_message()
            tl = last.lower().strip()
            if last and tl not in ("merke dir das", "speicher das", "merke dir das."):
                content = last
            else:
                return SkillResult(
                    success=False,
                    message="Was soll ich mir merken? Sag mir etwas — z.B. 'Ich heisse Marc' oder 'Ich wohne in Zürich'."
                )
        long_term.save_note(content, tags="personal")
        return SkillResult(success=True, message=f"Gespeichert! Ich werde mich an '{content}' erinnern.")

    # ── read ──────────────────────────────────────────────────────────────────

    def _read(self) -> SkillResult:
        notes = [n for n in long_term.get_notes(100) if n.get("tags") == "personal"]
        if not notes:
            return SkillResult(
                success=True,
                message=(
                    "Ich habe noch keine persönlichen Informationen über dich.\n"
                    "Sag mir z.B. 'Ich heisse X' oder 'Ich wohne in Y' — dann merke ich mir das."
                ),
            )
        lines = [f"• {n['content']}" for n in notes]
        return SkillResult(success=True, message="Das weiss ich über dich:\n" + "\n".join(lines))

    # ── delete ────────────────────────────────────────────────────────────────

    def _delete(self, entities: dict) -> SkillResult:
        scope = entities.get("scope", "last")
        if scope == "all":
            notes = [n for n in long_term.get_notes(1000) if n.get("tags") == "personal"]
            for n in notes:
                long_term.delete_note(n["id"])
            count = len(notes)
            if count == 0:
                return SkillResult(success=True, message="Keine persönlichen Daten vorhanden.")
            return SkillResult(success=True, message=f"Alle {count} persönlichen Einträge gelöscht.")

        # Delete most recent personal note
        notes = [n for n in long_term.get_notes(50) if n.get("tags") == "personal"]
        if not notes:
            any_notes = long_term.get_notes(1)
            if any_notes:
                long_term.delete_note(any_notes[0]["id"])
                return SkillResult(success=True, message=f"Gelöscht: '{any_notes[0]['content']}'")
            return SkillResult(success=True, message="Keine gespeicherten Einträge gefunden.")
        long_term.delete_note(notes[0]["id"])
        return SkillResult(success=True, message=f"Gelöscht: '{notes[0]['content']}'")
