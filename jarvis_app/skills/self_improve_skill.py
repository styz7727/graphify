"""Self-improvement: analyse action log, spot patterns, suggest improvements."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel


class SelfImproveSkill(BaseSkill):
    name = "self_improve"
    description = "Jarvis analysiert seine eigenen Logs und schlägt Verbesserungen vor"
    keywords = ["analysiere dich", "selbstanalyse", "was kannst du verbessern",
                "jarvis selbstverbesserung", "zeig deine schwächen"]
    safety_level = SafetyLevel.SAFE
    examples = [
        "Analysiere dich selbst",
        "Was kannst du verbessern?",
        "Selbstanalyse starten",
    ]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        from jarvis_app import config
        log_path = config.ACTION_LOG_PATH
        entries = _load_log(log_path)

        if not entries:
            return SkillResult(
                success=True,
                message=(
                    "Noch keine Aktionen protokolliert.\n"
                    "Nutz mich ein bisschen mehr — dann kann ich Muster erkennen."
                ),
            )

        report = _build_report(entries)
        return SkillResult(success=True, message=report)


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return entries[-200:]   # last 200 entries


def _build_report(entries: list[dict]) -> str:
    intents  = Counter(e.get("intent", "?")  for e in entries)
    decisions = Counter(e.get("decision", "?") for e in entries)

    top5 = intents.most_common(5)
    total = len(entries)
    blocked   = decisions.get("blocked",   0)
    cancelled = decisions.get("cancelled", 0)
    errors    = sum(1 for e in entries if "error" in e.get("decision", "").lower())

    lines = [f"Selbst-Analyse ({total} Aktionen):"]
    lines.append("")
    lines.append("Häufigste Befehle:")
    for intent, count in top5:
        pct = int(100 * count / total)
        lines.append(f"  • {intent}: {count}× ({pct}%)")

    lines.append("")
    lines.append("Statistik:")
    lines.append(f"  • Blockiert: {blocked}×")
    lines.append(f"  • Abgebrochen: {cancelled}×")
    lines.append(f"  • Fehler: {errors}×")

    lines.append("")
    suggestions = _suggestions(intents, blocked, cancelled, errors, total)
    if suggestions:
        lines.append("Vorschläge:")
        for s in suggestions:
            lines.append(f"  → {s}")

    return "\n".join(lines)


def _suggestions(
    intents: Counter,
    blocked: int,
    cancelled: int,
    errors: int,
    total: int,
) -> list[str]:
    s = []
    if blocked / max(total, 1) > 0.1:
        s.append("Viele blockierte Befehle — überprüfe die erlaubten Befehle in den Einstellungen.")
    if cancelled / max(total, 1) > 0.2:
        s.append("Viele abgebrochene Aktionen — evtl. Bestätigungsdialog zu häufig?")
    if errors / max(total, 1) > 0.05:
        s.append("Hohe Fehlerrate — starte den Debug-Test (🐛) für Details.")
    kq = intents.get("knowledge_query", 0)
    if kq / max(total, 1) > 0.5:
        s.append("Mehr als die Hälfte sind Wissensfragen — ein LLM-Backend wäre hilfreich.")
    if not s:
        s.append("Alles sieht gut aus! Nutzungsmuster sind ausgewogen.")
    return s
