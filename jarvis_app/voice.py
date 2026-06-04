"""Text-to-speech via edge-tts + Windows winmm playback. (STT added in v2)"""
from __future__ import annotations

import asyncio
import ctypes
import os
import sys
import tempfile
import threading

from jarvis_app import config


def speak(text: str) -> None:
    """Speak text in a background thread — non-blocking."""
    if not config.tts_enabled():
        return
    threading.Thread(target=_speak_sync, args=(text,), daemon=True).start()


def _speak_sync(text: str) -> None:
    try:
        asyncio.run(_speak_async(text))
    except Exception as e:
        print(f"[TTS] Fehler: {e}")


async def _speak_async(text: str) -> None:
    try:
        import edge_tts
    except ImportError:
        print("[TTS] edge-tts fehlt. Führe 'uv sync --extra jarvis-app' aus.")
        return

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    try:
        await edge_tts.Communicate(text, config.tts_voice()).save(tmp)
        _play_mp3(tmp)
    except Exception as e:
        print(f"[TTS] Ausgabe-Fehler: {e}")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _play_mp3(path: str) -> None:
    """Play MP3 synchronously using Windows winmm (no extra deps)."""
    try:
        winmm = ctypes.windll.winmm
        alias = "jarvis_tts_out"
        escaped = path.replace("\\", "\\\\")
        winmm.mciSendStringW(f'open "{escaped}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
        winmm.mciSendStringW(f"close {alias}", None, 0, None)
    except Exception as e:
        print(f"[TTS] Wiedergabe-Fehler: {e}")
