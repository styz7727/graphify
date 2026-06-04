"""Load graphify-out/graph.json and answer questions via LLM."""
from __future__ import annotations

import json
from pathlib import Path


class Knowledge:
    def __init__(self, graph_path: Path) -> None:
        self.graph_path = graph_path
        self._graph: dict | None = None
        self._backend: str | None = None

    # ── graph loading ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._graph is None:
            if not self.graph_path.exists():
                raise FileNotFoundError(
                    f"Kein Graph unter {self.graph_path}. "
                    "Führe zuerst 'graphify .' im Projektordner aus."
                )
            with open(self.graph_path, encoding="utf-8") as f:
                self._graph = json.load(f)
        return self._graph

    def _get_backend(self) -> str:
        if self._backend is None:
            from graphify.llm import detect_backend
            backend = detect_backend()
            if backend is None:
                raise RuntimeError(
                    "Kein LLM-Backend konfiguriert. "
                    "Setze ANTHROPIC_API_KEY oder ein anderes API-Key."
                )
            self._backend = backend
        return self._backend

    # ── public interface ───────────────────────────────────────────────────────

    def ask(self, question: str) -> str:
        """Answer a free-form question using the graph + LLM."""
        from graphify.llm import _call_llm
        graph = self._load()

        node_lines = [
            f"- {n['label']} ({n.get('source_file', '')})"
            for n in graph.get("nodes", [])[:150]
        ]
        edge_lines = [
            f"- {e['source']} → {e['target']} [{e.get('relation', '')}]"
            for e in graph.get("edges", [])[:150]
        ]
        graph_ctx = "NODES:\n" + "\n".join(node_lines) + "\n\nEDGES:\n" + "\n".join(edge_lines)

        prompt = (
            "Du bist Jarvis, ein präziser Codebasis-Assistent. "
            "Nutze den folgenden Wissengraph um die Frage zu beantworten.\n\n"
            f"{graph_ctx}\n\n"
            f"Frage: {question}\n\n"
            "Antworte kurz und direkt auf Deutsch (max. 3 Sätze)."
        )
        return _call_llm(prompt, backend=self._get_backend(), max_tokens=300)

    def god_nodes(self) -> list[str]:
        """Return the 5 highest-degree node labels."""
        graph = self._load()
        degree: dict[str, int] = {}
        for e in graph.get("edges", []):
            degree[e["source"]] = degree.get(e["source"], 0) + 1
            degree[e["target"]] = degree.get(e["target"], 0) + 1
        top5 = sorted(degree.items(), key=lambda x: -x[1])[:5]
        id_to_label = {n["id"]: n["label"] for n in graph.get("nodes", [])}
        return [id_to_label.get(nid, nid) for nid, _ in top5]

    def summary(self) -> str:
        """One-sentence graph summary with god nodes."""
        graph = self._load()
        n_nodes = len(graph.get("nodes", []))
        n_edges = len(graph.get("edges", []))
        gods = self.god_nodes()
        return (
            f"Der Graph hat {n_nodes} Knoten und {n_edges} Kanten. "
            f"Zentrale Komponenten: {', '.join(gods)}."
        )
