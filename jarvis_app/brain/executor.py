"""Execute a plan: route each Step through Safety → Skill → Result."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from jarvis_app.brain.planner import Step
from jarvis_app.safety.permissions import SafetyLevel
from jarvis_app.safety import action_log
from jarvis_app.skills.base_skill import SkillResult


@dataclass
class ExecutionResult:
    step: Step
    skill_result: SkillResult | None
    decision: str        # "executed" | "confirmed" | "cancelled" | "blocked"


def execute(
    steps: list[Step],
    confirm_fn: Callable[[str], bool],
) -> list[ExecutionResult]:
    """Run each step. confirm_fn(description) → bool is called for CONFIRM steps."""
    results: list[ExecutionResult] = []

    for step in steps:
        if step.safety_level == SafetyLevel.BLOCKED or step.intent == "blocked":
            action_log.log(step.intent, step.description, "blocked", "blocked")
            results.append(ExecutionResult(step=step, skill_result=None, decision="blocked"))
            continue

        if step.safety_level == SafetyLevel.CONFIRM:
            confirmed = confirm_fn(step.description)
            if not confirmed:
                action_log.log(step.intent, step.description, "confirm", "cancelled")
                results.append(ExecutionResult(step=step, skill_result=None, decision="cancelled"))
                continue
            action_log.log(step.intent, step.description, "confirm", "confirmed")

        # Execute the skill
        skill_result = _run_skill(step)
        decision = "executed"
        action_log.log(
            step.intent, step.description,
            step.safety_level.value,
            decision,
            skill_result.message if skill_result else ""
        )
        results.append(ExecutionResult(step=step, skill_result=skill_result, decision=decision))

    return results


def _run_skill(step: Step) -> SkillResult:
    from jarvis_app.skills import skill_registry

    # Special handling for "help" intent — return rich capability list
    if step.intent == "help":
        return _help_response()

    # Handle local Jarvis identity questions without API call
    if step.intent == "knowledge_query":
        local = _local_response(step.entities.get("query", ""))
        if local:
            return local

    skill = skill_registry.get(step.intent)
    if skill:
        return skill.handle(step.intent, step.entities)

    # Fallback: knowledge query via LLM
    return _knowledge_query(step.entities.get("query", step.entities.get("content", "")))


def _local_response(question: str) -> SkillResult | None:
    """Answer questions about Jarvis itself without an API call."""
    q = question.lower()
    if any(k in q for k in ("wer bist du", "was bist du", "was ist jarvis", "bist du jarvis")):
        return SkillResult(
            success=True,
            message=(
                "Ich bin Jarvis — dein persönlicher Windows-Assistent.\n"
                "Ich kann Notizen speichern, Apps öffnen, das Wetter abrufen, "
                "Git-Logs zusammenfassen und vieles mehr.\n"
                "Sag 'Was kannst du?' für eine vollständige Liste."
            ),
        )
    if any(k in q for k in ("wie geht es dir", "wie geht's", "alles okay")):
        return SkillResult(success=True, message="Mir geht es gut, danke! Womit kann ich dir helfen?")
    if any(k in q for k in ("danke", "danke schön", "merci", "thank")):
        return SkillResult(success=True, message="Gern geschehen! Kann ich noch etwas für dich tun?")
    return None


def _help_response() -> SkillResult:
    lines = [
        "Das kann ich für dich tun:\n",
        "🗣️  Sprachsteuerung",
        "  • F9 halten → sprechen → loslassen",
        "  • 'Hey Jarvis' (wenn Wake Word aktiviert)",
        "",
        "📝  Notizen & Erinnerungen",
        "  • 'Notiere dir: ...'  — Notiz speichern",
        "  • 'Was habe ich notiert?'  — Notizen lesen",
        "  • 'Erinnere mich an ... um 15:00'",
        "",
        "🧠  Persönliches Gedächtnis",
        "  • 'Ich heisse Marc'  — dauerhaft merken",
        "  • 'Was weisst du über mich?'",
        "  • 'Vergiss das'  — letzten Eintrag löschen",
        "",
        "🌤️  Wetter & Infos",
        "  • 'Wie ist das Wetter?'",
        "  • 'Wetter in Zürich'",
        "",
        "💻  Apps & Browser",
        "  • 'Öffne Chrome'  • 'Öffne VS Code'",
        "  • 'Öffne die Webseite https://...'",
        "  • 'Suche im Internet nach ...'",
        "",
        "📊  Entwickler",
        "  • 'Letzte Commits'  • 'Git Änderungen'",
        "  • 'TradingView BTC'",
        "",
        "🔍  Selbst-Analyse",
        "  • 'Analysiere dich selbst'",
        "  • 'Jarvis Diagnose'",
    ]
    return SkillResult(success=True, message="\n".join(lines))


def _knowledge_query(question: str) -> SkillResult:
    """Answer a free-form question using graphify knowledge graph + LLM."""
    if not question.strip():
        return SkillResult(success=False, message="Ich habe deine Frage nicht verstanden. Kannst du sie anders formulieren?")
    try:
        from jarvis_app import config
        from jarvis_app.personality import build_prompt
        from graphify.llm import _call_llm, detect_backend

        graph_ctx = _load_graph_context(config.graph_path())
        backend = detect_backend()

        if not backend:
            # Try auto-detecting Ollama
            backend = _try_ollama_backend()

        if not backend:
            return SkillResult(
                success=False,
                message=_no_backend_message(),
            )

        prompt = build_prompt(question, [], graph_ctx)
        answer = _call_llm(prompt, backend=backend, max_tokens=400)
        return SkillResult(success=True, message=answer)
    except Exception as e:
        return SkillResult(success=False, message=f"Antwort nicht möglich: {e}")


def _try_ollama_backend():
    """If Ollama is running, configure it as the LLM backend."""
    try:
        import os
        from jarvis_app.ollama_check import is_available, get_first_model
        if not is_available():
            return None
        model = get_first_model()
        if not model:
            return None
        # Set env so graphify's detect_backend() picks it up
        if not os.environ.get("OLLAMA_BASE_URL"):
            os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        if not os.environ.get("OLLAMA_MODEL"):
            os.environ["OLLAMA_MODEL"] = model
        from graphify.llm import detect_backend
        return detect_backend()
    except Exception:
        return None


def _no_backend_message() -> str:
    from jarvis_app.ollama_check import is_available, get_models
    lines = ["Kein KI-Backend gefunden. So aktivierst du eines:\n"]
    lines.append("[Cloud] ANTHROPIC_API_KEY=sk-...  (claude.ai/settings)")
    lines.append("        OPENAI_API_KEY=sk-...     (platform.openai.com)")
    lines.append("")
    if is_available():
        models = get_models()
        if models:
            lines.append(f"[OK] Ollama laeuft ({', '.join(models[:2])}) — aber nicht konfiguriert.")
            lines.append("     Setze: OLLAMA_BASE_URL=http://localhost:11434")
        else:
            lines.append("[!] Ollama laeuft, aber kein Modell geladen.")
            lines.append("    Lade ein Modell: ollama pull mistral")
    else:
        lines.append("[Lokal] Ollama installieren: ollama.com")
        lines.append("        Modell laden:       ollama pull mistral")
        lines.append("        Server starten:     ollama serve")
    return "\n".join(lines)


def _load_graph_context(graph_path) -> str:
    try:
        import json
        with open(graph_path, encoding="utf-8") as f:
            g = json.load(f)
        nodes = g.get("nodes", [])[:100]
        edges = g.get("edges", [])[:100]
        node_lines = [f"- {n['label']} ({n.get('source_file','')})" for n in nodes]
        edge_lines = [f"- {e['source']}→{e['target']} [{e.get('relation','')}]" for e in edges]
        return "NODES:\n" + "\n".join(node_lines) + "\n\nEDGES:\n" + "\n".join(edge_lines)
    except Exception:
        return ""
