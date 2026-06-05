"""Debug & Diagnose panel — 4 tabs: System-Check, Log, Selbst-Analyse, Info."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from jarvis_app import config

_VERSION = "6"


class DebugPanel(QDialog):
    """Debug & Diagnose dialog — Jarvis v6."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Jarvis — Debug & Diagnose (v6)")
        self.resize(660, 540)
        self.setStyleSheet("""
            QDialog   { background: #1a1a2e; }
            QLabel    { color: #e0e0e0; }
            QTextEdit { background: #0d1117; color: #c9d1d9;
                        border: 1px solid #30363d; border-radius: 4px;
                        font-family: Consolas, 'Courier New', monospace;
                        font-size: 11px; padding: 6px; }
            QTabWidget::pane { border: none; background: #1a1a2e; }
            QTabBar::tab { background: #16213e; color: #888; padding: 7px 15px; }
            QTabBar::tab:selected { background: #1a1a2e; color: #4ecca3;
                                    border-bottom: 2px solid #4ecca3; }
        """)
        self._tabs: QTabWidget | None = None
        self._build_ui()

    # ── shell ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_check_tab(),   "🩺 System-Check")
        self._tabs.addTab(self._build_log_tab(),     "📋 Aktions-Log")
        self._tabs.addTab(self._build_analyse_tab(), "💡 Selbst-Analyse")
        self._tabs.addTab(self._build_info_tab(),    "ℹ️ Info")
        outer.addWidget(self._tabs)

        # ── bottom bar ────────────────────────────────────────────────────────
        bar = QWidget()
        h   = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)

        refresh_btn = QPushButton("🔄 Aktualisieren")
        refresh_btn.setStyleSheet(_BTN)
        refresh_btn.clicked.connect(self._refresh)

        h.addWidget(refresh_btn)
        h.addStretch()

        close_btn = QPushButton("Schließen")
        close_btn.setStyleSheet(_BTN)
        close_btn.clicked.connect(self.accept)
        h.addWidget(close_btn)
        outer.addWidget(bar)

    def _refresh(self) -> None:
        """Rebuild all tabs in place."""
        if not self._tabs:
            return
        builders = [
            ("🩺 System-Check",   self._build_check_tab),
            ("📋 Aktions-Log",    self._build_log_tab),
            ("💡 Selbst-Analyse", self._build_analyse_tab),
            ("ℹ️ Info",           self._build_info_tab),
        ]
        current = self._tabs.currentIndex()
        while self._tabs.count():
            self._tabs.removeTab(0)
        for title, builder in builders:
            self._tabs.addTab(builder(), title)
        self._tabs.setCurrentIndex(current)

    # ── Tab 1: System-Check ───────────────────────────────────────────────────

    def _build_check_tab(self) -> QWidget:
        from jarvis_app.startup_check import run_startup_checks, summary

        w  = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(14, 14, 14, 10)
        vl.setSpacing(7)

        results = run_startup_checks()
        _IC = {"ok": "✅", "warn": "⚠️", "error": "❌"}
        _CL = {"ok": "#4ecca3", "warn": "#ffa500", "error": "#e05555"}

        for r in results:
            row = QWidget()
            h   = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(10)

            lbl_name = QLabel(f"{_IC[r.status]}  {r.name}")
            lbl_name.setFixedWidth(210)
            lbl_name.setStyleSheet(f"color:{_CL[r.status]}; font-weight:bold;")

            lbl_msg = QLabel(r.message)
            lbl_msg.setStyleSheet("color:#aaa; font-size:11px;")
            lbl_msg.setWordWrap(True)

            h.addWidget(lbl_name)
            h.addWidget(lbl_msg, 1)
            vl.addWidget(row)

        # ── Ollama status ──────────────────────────────────────────────────────
        from jarvis_app.ollama_check import status_text
        ollama_row = QWidget()
        oh = QHBoxLayout(ollama_row)
        oh.setContentsMargins(0, 0, 0, 0)
        oh.setSpacing(10)
        ollama_text = status_text()
        is_ok = "läuft" in ollama_text and "kein Modell" not in ollama_text
        ollama_ic = "✅" if is_ok else ("⚠️" if "läuft" in ollama_text else "ℹ️")
        ollama_color = "#4ecca3" if is_ok else ("#ffa500" if "läuft" in ollama_text else "#666")
        lbl_oname = QLabel(f"{ollama_ic}  Ollama (lokal)")
        lbl_oname.setFixedWidth(210)
        lbl_oname.setStyleSheet(f"color:{ollama_color}; font-weight:bold;")
        lbl_omsg = QLabel(ollama_text)
        lbl_omsg.setStyleSheet("color:#aaa; font-size:11px;")
        lbl_omsg.setWordWrap(True)
        oh.addWidget(lbl_oname)
        oh.addWidget(lbl_omsg, 1)
        vl.addWidget(ollama_row)

        vl.addStretch()

        sum_lbl = QLabel(summary(results))
        sum_lbl.setStyleSheet("color:#4ecca3; font-style:italic; font-size:11px;")
        vl.addWidget(sum_lbl)
        return w

    # ── Tab 2: Aktions-Log ────────────────────────────────────────────────────

    def _build_log_tab(self) -> QWidget:
        w  = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(8, 8, 8, 8)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(self._load_log())
        vl.addWidget(txt)
        return w

    def _load_log(self) -> str:
        path = config.ACTION_LOG_PATH
        if not path.exists():
            return "Noch keine Einträge im Aktions-Log."
        try:
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            out   = []
            for line in lines[-50:]:
                try:
                    d      = json.loads(line)
                    ts     = str(d.get("ts", ""))[:19]
                    intent = d.get("intent", "?")
                    dec    = d.get("decision", "?")
                    res    = str(d.get("result", ""))[:80]
                    out.append(f"[{ts}] {intent:<22} → {dec:<10}  {res}")
                except Exception:
                    out.append(line[:120])
            return "\n".join(out) if out else "Log leer."
        except Exception as exc:
            return f"Fehler beim Lesen: {exc}"

    # ── Tab 3: Selbst-Analyse ─────────────────────────────────────────────────

    def _build_analyse_tab(self) -> QWidget:
        w  = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(8, 8, 8, 8)
        vl.setSpacing(6)

        # ── analysis text ─────────────────────────────────────────────────────
        analyse_txt = QTextEdit()
        analyse_txt.setReadOnly(True)
        analyse_txt.setPlainText(self._build_analysis())
        vl.addWidget(analyse_txt, stretch=2)

        # ── git status ────────────────────────────────────────────────────────
        git_lbl = QLabel("Git-Status (nur lesen)")
        git_lbl.setStyleSheet("color:#4ecca3; font-weight:bold; font-size:11px;")
        vl.addWidget(git_lbl)

        git_txt = QTextEdit()
        git_txt.setReadOnly(True)
        git_txt.setFixedHeight(100)
        git_txt.setPlainText(self._git_status())
        vl.addWidget(git_txt)

        # ── claude prompt generator ───────────────────────────────────────────
        prompt_row = QWidget()
        ph = QHBoxLayout(prompt_row)
        ph.setContentsMargins(0, 0, 0, 0)

        self._prompt_txt = QTextEdit()
        self._prompt_txt.setReadOnly(True)
        self._prompt_txt.setFixedHeight(90)
        self._prompt_txt.setPlaceholderText(
            "Klicke 'Claude-Code-Prompt erzeugen' um einen Analyse-Prompt zu generieren."
        )

        gen_btn = QPushButton("Claude-Code-Prompt erzeugen")
        gen_btn.setStyleSheet(_BTN)
        gen_btn.setFixedWidth(240)
        gen_btn.clicked.connect(self._generate_claude_prompt)

        copy_btn = QPushButton("Kopieren")
        copy_btn.setStyleSheet(_BTN)
        copy_btn.setFixedWidth(80)
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self._prompt_txt.toPlainText())
        )

        ph.addWidget(gen_btn)
        ph.addWidget(copy_btn)
        vl.addWidget(prompt_row)
        vl.addWidget(self._prompt_txt)

        return w

    def _build_analysis(self) -> str:
        path = config.ACTION_LOG_PATH
        if not path.exists():
            return "Noch kein Aktions-Log — erst einige Befehle ausprobieren.\n\n" \
                   "Vorschlag: Starte Jarvis und teste F9 Push-to-talk oder\n" \
                   "aktiviere das Wake Word in den Einstellungen."

        from collections import Counter
        intents:   Counter = Counter()
        decisions: Counter = Counter()

        try:
            for line in path.read_text(encoding="utf-8").strip().splitlines():
                try:
                    d = json.loads(line)
                    intents[d.get("intent", "?")] += 1
                    decisions[d.get("decision", "?")] += 1
                except Exception:
                    pass
        except Exception as exc:
            return f"Fehler beim Lesen: {exc}"

        total = sum(intents.values())
        if total == 0:
            return "Log vorhanden, aber noch keine Befehle ausgeführt."

        lines = [f"=== Selbst-Analyse ({total} Befehle gesamt) ===", ""]

        lines.append("── Meistgenutzte Funktionen ──")
        for intent, count in intents.most_common(6):
            pct = count / total * 100
            lines.append(f"  {intent:<28} {count:4d}x  ({pct:.0f}%)")

        lines += ["", "── Entscheidungen ──"]
        for dec, count in decisions.most_common():
            lines.append(f"  {dec:<16} {count:4d}x")

        # Suggestions
        lines += ["", "── Verbesserungs-Vorschläge ──"]
        suggestions = _generate_suggestions(intents, decisions, total)
        lines += suggestions

        lines += [
            "",
            "── Sichere Update-Vorschläge ──",
            "  Führe diesen Befehl aus um alle Abhängigkeiten zu aktualisieren:",
            "  → uv sync --extra jarvis-app",
            "  (nie automatisch, immer manuell bestätigen)",
        ]
        return "\n".join(lines)

    def _git_status(self) -> str:
        repo = _find_repo_root()
        if repo is None:
            return "Git-Repository nicht gefunden."
        try:
            parts = []
            for args in [
                ["git", "branch", "--show-current"],
                ["git", "status", "--short"],
                ["git", "log", "--oneline", "-5"],
            ]:
                r = subprocess.run(args, cwd=repo, capture_output=True, text=True, timeout=4)
                if r.returncode == 0 and r.stdout.strip():
                    label = {
                        "--show-current": "Branch",
                        "--short":        "Änderungen",
                        "--oneline":      "Letzte Commits",
                    }.get(args[-1], "")
                    parts.append(f"{label}:\n{r.stdout.strip()}")
            return "\n\n".join(parts) if parts else "Keine git-Informationen."
        except Exception as exc:
            return f"git-Check fehlgeschlagen: {exc}"

    def _generate_claude_prompt(self) -> None:
        from jarvis_app.startup_check import run_startup_checks, summary as chk_summary

        checks   = run_startup_checks()
        chk_text = "\n".join(
            f"  {'OK' if r.status=='ok' else 'WARN' if r.status=='warn' else 'ERR'}"
            f"  {r.name}: {r.message}"
            for r in checks
        )

        errors = []
        if config.ACTION_LOG_PATH.exists():
            try:
                for line in config.ACTION_LOG_PATH.read_text(encoding="utf-8").strip().splitlines()[-20:]:
                    d = json.loads(line)
                    if d.get("decision") in ("error", "blocked"):
                        ts     = str(d.get("ts", ""))[:16]
                        intent = d.get("intent", "?")
                        res    = str(d.get("result", ""))[:80]
                        errors.append(f"  [{ts}] {intent}: {res}")
            except Exception:
                pass

        repo    = _find_repo_root() or "unbekannt"
        branch  = _git_branch(repo)
        date    = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""# Jarvis v{_VERSION} Selbstanalyse — {date}
Repository: {repo}  Branch: {branch}

## System-Check
{chk_text or "  Keine Ergebnisse"}

## Letzte Fehler/Blockierungen (max 20)
{chr(10).join(errors) if errors else "  Keine Fehler im Log"}

## Aufgabe für Claude Code
Analysiere den Code in jarvis_app/ basierend auf den obigen Daten.
Identifiziere die wichtigsten Verbesserungen für Stabilität und Benutzerfreundlichkeit.
Berücksichtige die bestehende Sicherheitsarchitektur (safety/, permissions.py).
Schlage konkrete Code-Änderungen vor, aber ändere nichts automatisch.
Zeige mir zuerst nur den Plan und frage dann um Bestätigung.
"""
        self._prompt_txt.setPlainText(prompt)

    # ── Tab 4: Info ───────────────────────────────────────────────────────────

    def _build_info_tab(self) -> QWidget:
        w  = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(8, 8, 8, 8)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(self._build_info())
        vl.addWidget(txt)
        return w

    def _build_info(self) -> str:
        lines = [f"=== Jarvis v{_VERSION} — System-Info ===", ""]
        lines += [f"Python:    {sys.version}", f"Platform:  {sys.platform}", ""]

        lines.append("=== Pakete ===")
        pkgs = [
            "PyQt6", "edge_tts", "sounddevice", "pynput",
            "faster_whisper", "openwakeword", "requests", "anthropic",
        ]
        for pkg in pkgs:
            try:
                mod = __import__(pkg)
                ver = getattr(mod, "__version__", "installiert")
                lines.append(f"  {pkg:<22} {ver}")
            except ImportError:
                lines.append(f"  {pkg:<22} NICHT INSTALLIERT")

        lines += ["", "=== API Key (maskiert) ==="]
        found = False
        for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
            key = os.environ.get(var, "")
            if key and len(key) > 8:
                masked = f"...{key[-4:]}"
                lines.append(f"  {var}: gesetzt ({masked}, Länge {len(key)})")
                found = True
        if not found:
            lines.append("  Kein API-Key gesetzt")

        lines += ["", "=== Konfiguration ==="]
        lines.append(f"  TTS Voice:   {config.tts_voice()}")
        lines.append(f"  TTS aktiv:   {config.tts_enabled()}")
        lines.append(f"  Wake Word:   {config.wake_word_enabled()}")
        lines.append(f"  WW-Threshold:{config.wake_word_threshold()}")
        lines.append(f"  Stadt:       {config.city()}")

        lines += ["", "=== Verzeichnisse ==="]
        lines.append(f"  App-Dir:    {config.APP_DIR}")
        lines.append(f"  Datenbank:  {config.DB_PATH}")
        lines.append(f"  Chat:       {config.CHAT_HISTORY_PATH}")
        lines.append(f"  Aktions-Log:{config.ACTION_LOG_PATH}")

        lines += ["", "=== Ollama (lokal) ==="]
        from jarvis_app.ollama_check import status_text as ollama_status
        lines.append(f"  {ollama_status()}")

        repo = _find_repo_root()
        lines += ["", "=== Repository ==="]
        lines.append(f"  Pfad:   {repo or 'nicht gefunden'}")
        if repo:
            lines.append(f"  Branch: {_git_branch(repo)}")

        return "\n".join(lines)


# ── helpers ───────────────────────────────────────────────────────────────────

def _find_repo_root() -> str | None:
    import jarvis_app
    start = Path(jarvis_app.__file__).parent.parent
    for p in [start] + list(start.parents)[:5]:
        if (p / ".git").exists():
            return str(p)
    return None


def _git_branch(repo: str) -> str:
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo, capture_output=True, text=True, timeout=3
        )
        return r.stdout.strip() if r.returncode == 0 else "?"
    except Exception:
        return "?"


def _generate_suggestions(intents, decisions, total: int) -> list[str]:
    from collections import Counter
    tips: list[str] = []

    blocked   = decisions.get("blocked", 0)
    confirmed = decisions.get("confirmed", 0)
    errors    = decisions.get("error", 0)

    if blocked > 3:
        tips.append(
            f"  • {blocked}x blockiert: Du versuchst oft gesperrte Aktionen. "
            "Schau in den Permission Center welche das sind."
        )
    if confirmed > 5:
        tips.append(
            f"  • {confirmed}x Bestätigung: Häufig bestätigte Aktionen könnten "
            "in Version 6 als 'vertrauenswürdig' markiert werden."
        )
    if errors > 2:
        tips.append(
            f"  • {errors}x Fehler: Prüfe ob alle Pakete aktuell sind → "
            "uv sync --extra jarvis-app"
        )

    top = intents.most_common(1)[0][0] if intents else None
    if top == "knowledge_query":
        tips.append(
            "  • Viele Wissensfragen: ANTHROPIC_API_KEY setzen für bessere Antworten."
        )
    if top == "weather":
        tips.append(
            "  • Häufige Wetter-Anfragen: Stadt in Einstellungen korrekt gesetzt?"
        )

    # key not set
    import os
    if not any(os.environ.get(k) for k in (
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"
    )):
        tips.append(
            "  • Kein API-Key: LLM-Antworten nicht verfügbar. "
            "Setze ANTHROPIC_API_KEY vor dem Starten."
        )

    if not tips:
        tips.append("  • Alles sieht gut aus — keine Verbesserungen nötig.")

    return tips


import sys   # noqa: E402  (needed for _build_info)

_BTN = (
    "QPushButton { background:#0f3460; color:#e0e0e0; border-radius:6px; "
    "padding:5px 14px; font-size:12px; }"
    "QPushButton:hover { background:#4ecca3; color:#1a1a2e; }"
)
