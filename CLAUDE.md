# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About this project

Graphify is a Python library and AI coding assistant skill that turns any folder of code, docs, PDFs, images, and videos into a queryable knowledge graph. Users invoke it via `/graphify .` in Claude Code and other AI assistants.

The PyPI package is `graphifyy` (double-y); the CLI command is `graphify`.

## Commands

**Install dependencies:**
```bash
uv sync --all-extras
```

**Run all tests:**
```bash
uv run pytest tests/ -q
```

**Run a single test or module:**
```bash
uv run pytest tests/test_build.py::test_build_from_json_node_count -q
uv run pytest tests/test_extract.py -q
uv run pytest tests/ -q -k "python"
```

**Lint:**
```bash
uv run ruff check
```

**Type check:**
```bash
uv run pyright
```

**Pre-commit hooks:**
```bash
uv run pre-commit run --all-files
```

## Architecture

The core pipeline is a linear chain of pure functions — no shared state, no side effects outside `graphify-out/`:

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

| Module | Function | Input → Output |
|--------|----------|----------------|
| `detect.py` | `collect_files(root)` | directory → `[Path]` |
| `extract.py` | `extract(path)` | file path → `{nodes, edges}` dict |
| `build.py` | `build_graph(extractions)` | list of extraction dicts → `nx.Graph` |
| `cluster.py` | `cluster(G)` | graph → graph with `community` attr on each node |
| `analyze.py` | `analyze(G)` | graph → analysis dict (god nodes, surprises, questions) |
| `report.py` | `render_report(G, analysis)` | graph + analysis → GRAPH_REPORT.md string |
| `export.py` | `export(G, out_dir, ...)` | graph → graph.json, graph.html, Obsidian vault, SVG |
| `serve.py` | `start_server(graph_path)` | graph file path → MCP stdio server |
| `cache.py` | `check_semantic_cache` / `save_semantic_cache` | files → (cached, uncached) split |
| `security.py` | validation helpers | URL / path / label → validated or raises |
| `validate.py` | `validate_extraction(data)` | extraction dict → raises on schema errors |
| `llm.py` | LLM backend abstraction | prompt → response (Claude, Gemini, OpenAI, Ollama, Bedrock) |
| `callflow_html.py` | `write_callflow_html(...)` | graphify-out files → Mermaid call-flow HTML |
| `__main__.py` | CLI entry point | — |

**Extraction schema** — every extractor returns:
```json
{
  "nodes": [{"id": "unique_string", "label": "human name", "source_file": "path", "source_location": "L42"}],
  "edges": [{"source": "id_a", "target": "id_b", "relation": "calls|imports|uses|...", "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"}]
}
```
`validate.py` enforces this schema before `build_graph()` consumes it.

**Confidence labels:**
- `EXTRACTED` — explicitly stated in source (import, direct call)
- `INFERRED` — reasonable deduction (call-graph second pass, co-occurrence)
- `AMBIGUOUS` — uncertain; flagged for human review in GRAPH_REPORT.md

## Adding a new language extractor

1. Add `extract_<lang>(path: Path) -> dict` in `extract.py` (tree-sitter parse → walk nodes → collect nodes/edges → call-graph second pass for INFERRED `calls` edges).
2. Register the file suffix in `extract()` dispatch and `collect_files()`.
3. Add the suffix to `CODE_EXTENSIONS` in `detect.py` and `_WATCHED_EXTENSIONS` in `watch.py`.
4. Add the tree-sitter package to `pyproject.toml` dependencies.
5. Add a fixture file to `tests/fixtures/` and tests to `tests/test_languages.py`.

## Security

All external input passes through `graphify/security.py`:
- URLs → `validate_url()` (http/https only) + blocks file:// redirects
- Fetched content → `safe_fetch()` (size cap, timeout)
- Graph file paths → `validate_graph_path()` (must resolve inside `graphify-out/`)
- Node labels → `sanitize_label()` (strips control chars, caps 256 chars, HTML-escapes)

See `SECURITY.md` for the full threat model.

## Using the knowledge graph

If `graphify-out/` exists in the project:
- Read `graphify-out/GRAPH_REPORT.md` before answering architecture or codebase questions — it contains pre-computed god nodes and community structure.
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files.
- After modifying code files, run `graphify update .` to keep the graph current (AST-only, no API cost).
