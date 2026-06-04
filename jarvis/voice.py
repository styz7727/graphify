"""Speech-to-text (faster-whisper) and text-to-speech (edge-tts) for Jarvis."""
from __future__ import annotations

import asyncio
import ctypes
import os
import sys
import tempfile
import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000
TTS_VOICE = "de-DE-ConradNeural"
_WHISPER_MODEL_SIZE = "base"


class Voice:
    def __init__(self) -> None:
        self._whisper = None

    def _load_whisper(self):
        if self._whisper is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                sys.exit(
                    "faster-whisper fehlt. Führe 'uv sync --extra jarvis' aus."
                )
            print("Lade Whisper-Modell (einmalig)...")
            self._whisper = WhisperModel(
                _WHISPER_MODEL_SIZE, device="cpu", compute_type="int8"
            )
        return self._whisper

    def record(self, stop: threading.Event) -> np.ndarray | None:
        """Record int16 audio until stop is set."""
        chunks: list[np.ndarray] = []

        def _cb(indata, frames, time, status):
            chunks.append(indata.copy())

        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=_cb
        ):
            stop.wait()

        return np.concatenate(chunks).flatten() if chunks else None

    def transcribe(self, audio: np.ndarray) -> str:
        model = self._load_whisper()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        try:
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio.tobytes())
            segments, _ = model.transcribe(tmp, language="de")
            return " ".join(s.text for s in segments).strip()
        finally:
            os.unlink(tmp)

    def speak(self, text: str) -> None:
        asyncio.run(self._speak_async(text))

    async def _speak_async(self, text: str) -> None:
        try:
            import edge_tts
        except ImportError:
            print("[TTS] edge-tts fehlt. Führe 'uv sync --extra jarvis' aus.")
            return

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        try:
            await edge_tts.Communicate(text, TTS_VOICE).save(tmp)
            _play_mp3(tmp)
        finally:
            os.unlink(tmp)


def _play_mp3(path: str) -> None:
    """Play an MP3 file synchronously using Windows winmm (no extra deps)."""
    winmm = ctypes.windll.winmm
    alias = "jarvis_tts"
    escaped = path.replace("\\", "\\\\")
    winmm.mciSendStringW(f'open "{escaped}" type mpegvideo alias {alias}', None, 0, None)
    winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
    winmm.mciSendStringW(f"close {alias}", None, 0, None)
