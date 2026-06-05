from __future__ import annotations
import subprocess
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel


class GitSkill(BaseSkill):
    name = "git_summary"
    description = "Letzte Git-Änderungen zusammenfassen"
    keywords = ["git", "letzte commits", "was hat sich geändert", "git änderungen",
                "fasse meine letzten git", "git status", "git log"]
    safety_level = SafetyLevel.SAFE
    examples = ["Fasse meine letzten Git-Änderungen zusammen", "Was hat sich geändert?"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        try:
            log = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                capture_output=True, text=True, timeout=10
            )
            if log.returncode != 0:
                return SkillResult(success=False, message="Kein Git-Repository gefunden.")

            raw = log.stdout.strip()
            if not raw:
                return SkillResult(success=True, message="Keine Commits gefunden.")

            # Ask LLM for a German summary
            summary = self._summarize(raw)
            return SkillResult(success=True, message=summary, data={"git_log": raw})
        except FileNotFoundError:
            return SkillResult(success=False, message="git ist nicht installiert oder nicht im PATH.")
        except Exception as e:
            return SkillResult(success=False, message=f"Git-Fehler: {e}")

    def _summarize(self, log: str) -> str:
        try:
            from graphify.llm import _call_llm, detect_backend
            backend = detect_backend()
            if not backend:
                return f"Letzte Commits:\n{log}"
            prompt = (
                f"Fasse diese Git-Commits in 2 Sätzen auf Deutsch zusammen:\n\n{log}\n\n"
                "Antworte nur mit der Zusammenfassung."
            )
            return _call_llm(prompt, backend=backend, max_tokens=150)
        except Exception:
            return f"Letzte Commits:\n{log}"
