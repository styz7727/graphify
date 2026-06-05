"""TTS via edge-tts + Windows winmm. STT via faster-whisper + sounddevice."""
from __future__ import annotations

import asyncio
import ctypes
import os
import tempfile
import threading
import time
from typing import TYPE_CHECKING

from jarvis_app import config

if TYPE_CHECKING:
    import numpy as np

# ── TTS guard — prevent duplicate / parallel speaks ───────────────────────────

_speak_lock    = threading.Lock()
_is_speaking   = False
_last_text     = ""
_last_time     = 0.0
_DEDUP_SECS    = 5.0   # same text within 5 s → skip


def speak(text: str) -> None:
    """Speak text in a background daemon thread (non-blocking).

    Guard rules:
    - TTS disabled in settings → silent
    - Identical text spoken within _DEDUP_SECS → skipped (dedup)
    - Another speak() is already running → new text replaces queue (last-wins)
    """
    global _last_text, _last_time

    if not config.tts_enabled():
        return

    now = time.monotonic()
    with _speak_lock:
        if text == _last_text and now - _last_time < _DEDUP_SECS:
            _log_tts("skip-dedup", text)
            return
        _last_text = text
        _last_time = now

    _log_tts("start", text)
    threading.Thread(target=_speak_guarded, args=(text,), daemon=True).start()


def _speak_guarded(text: str) -> None:
    global _is_speaking
    if _is_speaking:
        _log_tts("skip-busy", text)
        return
    _is_speaking = True
    try:
        _speak_sync(text)
    finally:
        _is_speaking = False


def _speak_sync(text: str) -> None:
    try:
        asyncio.run(_speak_async(text))
    except Exception as e:
        _log_tts("error", f"{e}")


async def _speak_async(text: str) -> None:
    try:
        import edge_tts
    except ImportError:
        print("[TTS] edge-tts fehlt — uv sync --extra jarvis-app")
        return
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    try:
        await edge_tts.Communicate(text, config.tts_voice()).save(tmp)
        _play_mp3(tmp)
        _log_tts("done", text)
    except Exception as e:
        _log_tts("error", f"{e}")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _play_mp3(path: str) -> None:
    try:
        winmm = ctypes.windll.winmm
        alias = "jarvis_tts_out"
        escaped = path.replace("\\", "\\\\")
        winmm.mciSendStringW(f'open "{escaped}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
        winmm.mciSendStringW(f"close {alias}", None, 0, None)
    except Exception as e:
        _log_tts("play-error", f"{e}")


def _log_tts(event: str, text: str) -> None:
    """Write a TTS event to the action log (no secrets, text truncated)."""
    try:
        from jarvis_app import config as _cfg
        import json
        from datetime import datetime
        entry = {
            "ts":     datetime.now().isoformat(timespec="seconds"),
            "intent": "_tts",
            "desc":   f"{event}: {text[:60]}",
            "level":  "tts",
            "decision": event,
        }
        with open(_cfg.ACTION_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── STT ───────────────────────────────────────────────────────────────────────

_SAMPLE_RATE = 16_000
_whisper_model = None
_model_lock = threading.Lock()


def record_audio(stop_event: threading.Event) -> "np.ndarray | None":
    """Record from default mic until stop_event is set. Returns float32 array at 16kHz."""
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        print("[STT] sounddevice fehlt — uv sync --extra jarvis-app")
        stop_event.wait()
        return None

    chunks: list = []

    def _cb(indata, frames, time, status):
        chunks.append(indata.copy())

    try:
        with sd.InputStream(samplerate=_SAMPLE_RATE, channels=1, dtype="float32", callback=_cb):
            stop_event.wait()
    except Exception as e:
        print(f"[STT] Aufnahme-Fehler: {e}")
        return None

    if not chunks:
        return None
    import numpy as np
    return np.concatenate(chunks, axis=0).flatten()


def transcribe(audio: "np.ndarray", language: str = "de") -> str:
    """Transcribe a float32 16kHz audio array to text."""
    model = _load_whisper()
    if model is None:
        return ""
    try:
        segments, _ = model.transcribe(audio, language=language, beam_size=1)
        return " ".join(s.text.strip() for s in segments).strip()
    except Exception as e:
        print(f"[STT] Transkriptions-Fehler: {e}")
        return ""


def record_until_silence(
    max_duration: float = 10.0,
    silence_duration: float = 2.0,
    silence_threshold: float = 0.015,
    grace_period: float = 0.5,
) -> "np.ndarray | None":
    """Record until silence_duration seconds of quiet, or max_duration reached.

    grace_period gives the user time to start speaking before silence detection
    activates.  silence_threshold is the RMS level below which audio is silent.
    """
    import time as _time
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        print("[STT] sounddevice fehlt")
        return None

    chunks: list = []
    stop_event    = threading.Event()
    silence_at: list = [None]
    started_at    = _time.monotonic()

    def _cb(indata, frames, t, status):
        chunk = indata.copy().flatten()
        chunks.append(chunk)
        if _time.monotonic() - started_at < grace_period:
            return
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        if rms < silence_threshold:
            if silence_at[0] is None:
                silence_at[0] = _time.monotonic()
            elif _time.monotonic() - silence_at[0] >= silence_duration:
                stop_event.set()
        else:
            silence_at[0] = None

    try:
        with sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=_cb,
        ):
            stop_event.wait(timeout=max_duration)
    except Exception as exc:
        print(f"[STT] Aufnahme-Fehler: {exc}")
        return None

    if not chunks:
        return None
    return np.concatenate(chunks).flatten()


def _load_whisper():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    with _model_lock:
        if _whisper_model is not None:
            return _whisper_model
        try:
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("[STT] Whisper-Modell geladen (tiny/cpu)")
        except ImportError:
            print("[STT] faster-whisper fehlt — uv sync --extra jarvis-app")
        except Exception as e:
            print(f"[STT] Modell-Fehler: {e}")
    return _whisper_model
