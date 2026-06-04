"""Launch whitelisted Windows applications."""
from __future__ import annotations

import os
import shlex
import subprocess

from jarvis_app import config


def launch(app_name: str) -> str:
    whitelist = config.app_whitelist()
    key = app_name.lower().strip()

    if key not in whitelist:
        available = ", ".join(sorted(whitelist.keys()))
        return f"'{app_name}' ist nicht in der Whitelist. Verfügbar: {available}"

    cmd = os.path.expandvars(whitelist[key])
    try:
        # Split only if it looks like a multi-arg command
        parts = shlex.split(cmd, posix=False) if " " in cmd else [cmd]
        subprocess.Popen(parts, shell=False)
        return f"{app_name.capitalize()} wird geöffnet."
    except FileNotFoundError:
        return f"Programm nicht gefunden: {cmd}"
    except Exception as e:
        return f"Fehler beim Starten von {app_name}: {e}"


def available_apps() -> list[str]:
    return sorted(config.app_whitelist().keys())
