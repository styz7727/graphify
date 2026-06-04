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

    skill = skill_registry.get(step.intent)
    if skill:
        return skill.handle(step.intent, step.entities)

    # Fallback: knowledge query via LLM
    return _knowledge_query(step.entities.get("query", step.entities.get("content", "")))


def _knowledge_query(question: str) -> SkillResult:
    """Answer a free-form question using graphify knowledge graph + LLM."""
    try:
        from jarvis_app import config
        from jarvis_app.personality import build_prompt
        from graphify.llm import _call_llm, detect_backend

        graph_ctx = _load_graph_context(config.graph_path())
        backend = detect_backend()
        if not backend:
            return SkillResult(success=False, message="Kein LLM-Backend konfiguriert. Bitte ANTHROPIC_API_KEY setzen.")

        prompt = build_prompt(question, [], graph_ctx)
        answer = _call_llm(prompt, backend=backend, max_tokens=400)
        return SkillResult(success=True, message=answer)
    except Exception as e:
        return SkillResult(success=False, message=f"Konnte nicht antworten: {e}")


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
