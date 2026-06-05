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

## Jarvis Desktop App (`jarvis_app/`) — Version 4

Full-featured Windows desktop assistant with voice I/O, intent routing, skills, and memory.

**Install deps:**
```bash
uv sync --extra jarvis-app
```

**Run:**
```bash
uv run python -m jarvis_app
```

**Input modes:**
- **F9 Push-to-talk** — hold F9, speak, release to transcribe and send
- **Wake Word** — say "Hey Jarvis" (requires openwakeword; enable in ⚙️ Settings)
- **Text** — type in the input field and press Enter / →

**Wake Word setup:**
1. Click ⚙️ in the title bar → enable "Hey Jarvis"
2. On first run the `hey_jarvis_v0.1` ONNX model is downloaded from HuggingFace (~1 MB)
3. The mic icon turns green when Wake Word is active
4. Speak your command; recording stops automatically after ~2 s of silence

**Manual model install (offline):**
```
# Download hey_jarvis_v0.1.onnx from:
# https://huggingface.co/davidscripka/OpenWakeWord
# Place in: <python-env>/Lib/site-packages/openwakeword/resources/models/
```

**Wake Word — privacy:**
- Audio is processed in-memory only; nothing is stored or transmitted
- The listener exits if Wake Word is disabled in settings
- The mic icon shows the current state at all times:
  - Grey border = idle (only F9 active)
  - Green border = Wake Word listening
  - Red background = recording in progress

**Mic status states:**
| State | Label | Mic icon |
|-------|-------|----------|
| idle | "F9 halten zum Sprechen" | grey |
| wake word active | "🟢 Wake Word aktiv — sage 'Hey Jarvis'" | green border |
| wake word detected | "🟡 'Hey Jarvis' erkannt — spreche deinen Befehl…" | red |
| recording (F9 or auto) | "🔴 Aufnahme läuft…" | red |
| transcribing | "⏳ Transkribiere…" | grey |

**Key files:**
| File | Role |
|------|------|
| `jarvis_app/wake_word.py` | `WakeWordListener(QThread)` — OpenWakeWord detection |
| `jarvis_app/voice.py` | STT (faster-whisper) + TTS (edge-tts) + `record_until_silence()` |
| `jarvis_app/config.py` | QSettings persistence; `wake_word_enabled()`, `wake_word_threshold()` |
| `jarvis_app/ui/overlay.py` | Main window; wires F9 + Wake Word + settings |
| `jarvis_app/ui/settings_panel.py` | Settings dialog (wake word toggle) |
| `jarvis_app/ui/push_to_talk.py` | F9 global key listener |

**Safety rules (unchanged from v3):**
- CONFIRM required for: apps, browser, web search, TradingView, focus modes
- BLOCKED always: shell exec, read secrets, send messages, delete files, install packages
- All actions logged to `~/.jarvis_app/action_log.jsonl`

## Jarvis assistant (`jarvis/`)

A push-to-talk voice assistant that answers questions about the codebase using the graphify knowledge graph.

**Install deps:**
```bash
uv sync --extra jarvis
```

**Run:**
```bash
python -m jarvis
```
Hold F9 to record, release to send. Requires `graphify-out/graph.json` (run `graphify .` first) and an LLM API key (`ANTHROPIC_API_KEY` or similar).

**Modules:**
| File | Role |
|---|---|
| `jarvis/voice.py` | STT via faster-whisper, TTS via edge-tts + Windows winmm playback |
| `jarvis/knowledge.py` | Loads graph.json, answers free-form questions via `graphify.llm._call_llm` |
| `jarvis/commands.py` | Keyword router → tests / god nodes / architecture / free LLM query |
| `jarvis/main.py` | pynput push-to-talk loop, spawns recording thread per keypress |

**Voice:** `de-DE-ConradNeural` (German male, edge-tts). Change `TTS_VOICE` in `voice.py` to switch.

**Adding a command:** add keywords to `_KEYWORDS` in `commands.py` and a handler branch in `route()`.
