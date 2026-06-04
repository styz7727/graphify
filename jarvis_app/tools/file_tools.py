"""Safe file search and reading — blocked paths excluded."""
from __future__ import annotations

import os
from pathlib import Path

_BLOCKED_DIRS = {
    ".ssh", ".aws", ".gnupg", "AppData\\Roaming\\Microsoft\\Credentials",
    "AppData\\Local\\Microsoft\\Credentials",
}
_BLOCKED_EXTENSIONS = {".env", ".key", ".pem", ".pfx", ".p12"}
_MAX_BYTES = 50_000


def is_safe_path(path: Path) -> bool:
    p = str(path).lower()
    if any(b.lower() in p for b in _BLOCKED_DIRS):
        return False
    if path.suffix.lower() in _BLOCKED_EXTENSIONS:
        return False
    return True


def read_file(path_str: str) -> str:
    path = Path(path_str).expanduser().resolve()
    if not is_safe_path(path):
        return f"Zugriff verweigert: {path}"
    if not path.exists():
        return f"Datei nicht gefunden: {path}"
    if path.stat().st_size > _MAX_BYTES:
        return f"Datei zu gross (> {_MAX_BYTES // 1000} KB): {path}"
    return path.read_text(encoding="utf-8", errors="replace")


def find_files(pattern: str, root: str = ".") -> list[str]:
    root_path = Path(root).resolve()
    try:
        matches = [
            str(p.relative_to(root_path))
            for p in root_path.rglob(pattern)
            if p.is_file() and is_safe_path(p)
        ]
        return matches[:50]
    except Exception as e:
        return [f"Fehler: {e}"]
