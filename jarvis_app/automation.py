"""Scheduled automations — skeleton for v4.

In v1, automations are defined but not yet triggered automatically.
Wire them up to QTimer in __main__.py in v4.
"""
from __future__ import annotations


def morning_briefing() -> str:
    """Tagesübersicht: Wetter + Erinnerungen. (v4: auto-run at 08:00)"""
    from jarvis_app.tools.weather import get_weather
    from jarvis_app.memory.reminders import get_today
    weather = get_weather()
    today = get_today()
    reminder_text = (
        "Heute: " + ", ".join(r["content"] for r in today)
        if today else "Keine Erinnerungen für heute."
    )
    return f"Guten Morgen! {weather} {reminder_text}"


def evening_summary() -> str:
    """Zusammenfassung des Tages. (v4: auto-run at 20:00)"""
    from jarvis_app.memory.episodic import today_summary
    actions = today_summary()
    if not actions:
        return "Heute wurden keine Aktionen aufgezeichnet."
    count = len(actions)
    intents = list({a["intent"] for a in actions})
    return f"Heute hast du {count} Aktionen ausgeführt: {', '.join(intents[:5])}."
