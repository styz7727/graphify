"""Classify user text into an intent + extract entities.

Pass 1: keyword matching (fast, no API cost)
Pass 2: LLM fallback for ambiguous text
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from jarvis_app.safety.permissions import is_blocked_input

# Priority-ordered: more specific patterns first to prevent early misfires
_PRIORITY: list[str] = [
    "memory_save", "memory_read", "memory_delete",
    "focus_mode", "tradingview", "browser_open", "web_search",
    "open_app", "notes_save", "notes_read",
    "reminders_set", "reminders_read",
    "git_summary", "weather", "calendar_prep",
    "self_improve", "diagnostics", "help", "knowledge_query",
]

_KEYWORDS: dict[str, list[str]] = {
    "memory_save": [
        "merke dir das", "speicher das dauerhaft",
        "ich heisse ", "mein name ist ", "ich bin geboren",
        "mein geburtstag ist ", "ich wohne in ", "ich arbeite als ",
        "ich spreche ", "meine sprache ist",
    ],
    "memory_read": [
        "was weisst du über mich", "was weißt du über mich",
        "was weisst du ueber mich", "was weisst du von mir",
        "was hast du über mich gespeichert", "was hast du ueber mich",
        "zeig meine gespeicherten", "meine persönlichen daten",
    ],
    "memory_delete": [
        "vergiss das", "vergiss alles über mich", "vergiss alles ueber mich",
        "lösch meine daten", "vergiss was du über mich weisst",
        "vergiss was du ueber mich", "vergiss meine daten",
    ],
    "focus_mode":      ["arbeitsmodus", "lernmodus", "tradingmodus", "schulmodus"],
    "tradingview":     ["tradingview", "kurs von ", "bitcoin chart", "btc chart",
                        "eth chart", "chart für", "chart von"],
    "browser_open":    ["öffne die webseite", "öffne url", "navigiere zu",
                        "gehe zu https", "gehe zu http"],
    "web_search":      ["suche im internet nach", "suche im web nach",
                        "google nach", "suche nach "],
    "open_app":        ["öffne teams", "öffne chrome", "öffne firefox",
                        "öffne explorer", "öffne notepad", "öffne vscode",
                        "starte teams", "starte chrome"],
    "notes_save":      ["notiere dir", "notiere:", "schreib auf",
                        "merke dir", "notiz:"],
    "notes_read":      ["was habe ich notiert", "zeig meine notizen", "meine notizen"],
    "reminders_set":   ["erinnere mich", "erinnerung setzen", "reminder setzen"],
    "reminders_read":  ["was steht heute an", "heutige erinnerungen", "meine erinnerungen"],
    "git_summary":     ["git log", "letzte commits", "git änderungen",
                        "was hat sich geändert", "fasse meine letzten git"],
    "weather":         ["wie ist das wetter", "wetter in ", "wetter heute",
                        "temperatur heute", "regnet es", "ist es kalt"],
    "calendar_prep":   ["termin mit ", "termin am ", "termin um "],
    "self_improve":    ["analysiere dich", "selbstanalyse", "was kannst du verbessern",
                        "jarvis selbstverbesserung", "zeig deine schwächen",
                        "selbst-analyse"],
    "diagnostics":     ["warum funktioniert jarvis", "jarvis diagnose", "selbstprüfung"],
    "help":            ["was kannst du", "befehle zeigen", "hilfe", " help",
                        "was kann jarvis", "zeig alle befehle"],
    "knowledge_query": ["was macht", "erkläre mir", "wie funktioniert",
                        "was ist ", "architektur von", "codebase"],
}

# ── entity extractors ─────────────────────────────────────────────────────────

def _extract(intent: str, text: str) -> dict:
    t  = text.strip()
    tl = t.lower()

    if intent == "memory_save":
        label_map = {
            "ich heisse ":         "Mein Name: ",
            "mein name ist ":      "Mein Name: ",
            "ich wohne in ":       "Ich wohne in: ",
            "ich arbeite als ":    "Ich arbeite als: ",
            "mein geburtstag ist ":"Geburtstag: ",
            "ich bin geboren ":    "Geburtstag: ",
            "ich spreche ":        "Sprache: ",
        }
        for marker, label in label_map.items():
            if marker in tl:
                idx  = tl.index(marker) + len(marker)
                fact = t[idx:].strip().rstrip(".")
                return {"content": label + fact}
        return {"content": ""}   # empty → memory_skill reads last message

    if intent == "memory_delete":
        if "alles" in tl or "alle" in tl or "gesamt" in tl:
            return {"scope": "all"}
        return {"scope": "last"}

    if intent == "open_app":
        for prefix in ("öffne ", "starte ", "launch "):
            if tl.startswith(prefix):
                return {"target": t[len(prefix):].strip()}
        m = re.search(r"(?:öffne|starte|launch)\s+(\w+)", tl)
        return {"target": m.group(1) if m else ""}

    if intent == "tradingview":
        for marker in ("tradingview ", "kurs von ", "chart für ", "chart von ",
                       "btc chart", "eth chart", "bitcoin chart"):
            if marker in tl:
                after = tl.split(marker, 1)[-1].strip()
                token = after.split()[0].upper() if after else "BTC"
                return {"symbol": token}
        tokens = [w for w in t.split() if w.isupper() and 2 <= len(w) <= 6]
        return {"symbol": tokens[0] if tokens else "BTC"}

    if intent == "web_search":
        for marker in ("suche im internet nach ", "suche im web nach ",
                       "google nach ", "suche nach "):
            if marker in tl:
                return {"query": t[tl.index(marker) + len(marker):].strip()}
        return {"query": t}

    if intent == "browser_open":
        m = re.search(r"https?://\S+", t)
        if m:
            return {"url": m.group(0)}
        for marker in ("gehe zu ", "navigiere zu ", "öffne url ", "öffne die webseite "):
            if marker in tl:
                return {"url": t[tl.index(marker) + len(marker):].strip()}
        return {"url": ""}

    if intent == "notes_save":
        for marker in ("notiere dir", "notiere:", "schreib auf", "merke dir", "notiz:"):
            if marker in tl:
                idx = tl.index(marker) + len(marker)
                return {"content": t[idx:].strip().lstrip(": ")}
        return {"content": t}

    if intent == "reminders_set":
        for marker in ("erinnere mich ", "erinnere mich an ", "erinnerung: "):
            if marker in tl:
                rest = t[tl.index(marker) + len(marker):]
                time_m = re.search(r"um\s+(\d{1,2}(?::\d{2})?(?:\s*uhr)?)", rest, re.I)
                due = time_m.group(0) if time_m else "unbekannte Zeit"
                content = re.sub(r"\s+um\s+\d{1,2}.*", "", rest, flags=re.I).strip()
                return {"content": content, "due": due}
        return {"content": t, "due": "unbekannte Zeit"}

    if intent == "focus_mode":
        for mode_kw, mode_id in [
            ("arbeitsmodus", "work"), ("lernmodus", "learn"),
            ("tradingmodus", "trading"), ("schulmodus", "school"),
        ]:
            if mode_kw in tl:
                return {"mode": mode_id}
        return {"mode": "work"}

    if intent == "weather":
        m = re.search(r"wetter in ([a-züöäßA-ZÜÖÄ]+)", tl)
        return {"city": m.group(1).capitalize() if m else None}

    return {}


# ── public dataclass ──────────────────────────────────────────────────────────

@dataclass
class IntentResult:
    intent: str
    entities: dict = field(default_factory=dict)
    raw_text: str = ""


def route(text: str, context: list[dict]) -> IntentResult:
    """Classify text → IntentResult. Uses keyword matching then LLM fallback."""
    if is_blocked_input(text):
        return IntentResult(intent="blocked", raw_text=text)

    tl = text.lower()

    # Handle simple affirmatives when there's a pending clarification
    from jarvis_app.memory.short_term import ShortTerm
    pending = ShortTerm().get_pending()
    if pending and tl.strip().rstrip(".!") in ("ja", "yes", "genau", "stimmt", "korrekt", "richtig", "ok", "okay"):
        ShortTerm().clear_pending()
        return IntentResult(
            intent=pending["intent"],
            entities=pending.get("entities", {}),
            raw_text=text,
        )

    for intent in _PRIORITY:
        for kw in _KEYWORDS.get(intent, []):
            if kw in tl:
                entities = _extract(intent, text)
                return IntentResult(intent=intent, entities=entities, raw_text=text)

    # LLM fallback — treat as knowledge query
    return IntentResult(intent="knowledge_query", entities={"query": text}, raw_text=text)
