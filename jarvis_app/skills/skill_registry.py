"""Dynamic skill registry — maps intents to skill instances."""
from __future__ import annotations

from jarvis_app.skills.base_skill import BaseSkill

_registry: dict[str, BaseSkill] = {}


def register(intent: str, skill: BaseSkill) -> None:
    _registry[intent] = skill


def get(intent: str) -> BaseSkill | None:
    return _registry.get(intent)


def all_skills() -> dict[str, BaseSkill]:
    return dict(_registry)


def _load_defaults() -> None:
    from jarvis_app.skills.weather_skill import WeatherSkill
    from jarvis_app.skills.tradingview_skill import TradingViewSkill
    from jarvis_app.skills.app_launcher_skill import AppLauncherSkill
    from jarvis_app.skills.browser_skill import BrowserSkill
    from jarvis_app.skills.notes_skill import NotesSkill
    from jarvis_app.skills.git_skill import GitSkill
    from jarvis_app.skills.focus_skill import FocusSkill
    from jarvis_app.skills.calendar_skill import CalendarSkill
    from jarvis_app.skills.diagnostics_skill import DiagnosticsSkill
    from jarvis_app.skills.memory_skill import MemorySkill
    from jarvis_app.skills.self_improve_skill import SelfImproveSkill

    register("weather",         WeatherSkill())
    register("tradingview",     TradingViewSkill())
    register("open_app",        AppLauncherSkill())
    register("browser_open",    BrowserSkill())
    register("web_search",      BrowserSkill())
    register("notes_save",      NotesSkill())
    register("notes_read",      NotesSkill())
    register("reminders_set",   NotesSkill())
    register("reminders_read",  NotesSkill())
    register("git_summary",     GitSkill())
    register("focus_mode",      FocusSkill())
    register("calendar_prep",   CalendarSkill())
    register("diagnostics",     DiagnosticsSkill())
    _mem = MemorySkill()
    register("memory_save",     _mem)
    register("memory_read",     _mem)
    register("memory_delete",   _mem)
    register("self_improve",    SelfImproveSkill())


_load_defaults()
