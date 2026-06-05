"""Windows autostart via HKCU registry — no admin rights required."""
from __future__ import annotations

import sys

_APP_NAME = "Jarvis"
_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_autostart_enabled() -> bool:
    """Return True if a Jarvis autostart entry exists in the current user's registry."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, _APP_NAME)
        return True
    except (ImportError, FileNotFoundError, OSError):
        return False


def set_autostart(enabled: bool) -> bool:
    """Add or remove the Windows autostart registry entry. Returns True on success."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_WRITE) as k:
            if enabled:
                cmd = f'"{sys.executable}" -m jarvis_app'
                winreg.SetValueEx(k, _APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, _APP_NAME)
                except FileNotFoundError:
                    pass   # already absent
        return True
    except ImportError:
        print("[Autostart] winreg nicht verfügbar (kein Windows?)")
        return False
    except Exception as exc:
        print(f"[Autostart] Fehler: {exc}")
        return False
