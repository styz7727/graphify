"""Jarvis — Push-to-talk Assistent für graphify-Projekte.

Starten:  python -m jarvis
Sprechen: F9 gedrückt halten → loslassen → Antwort wird vorgelesen.
Beenden:  Ctrl+C
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from jarvis.voice import SAMPLE_RATE, Voice
from jarvis.knowledge import Knowledge
from jarvis.commands import route

GRAPH_PATH = Path("graphify-out/graph.json")
MIN_AUDIO_SAMPLES = SAMPLE_RATE // 2  # ignore recordings shorter than 0.5 s


def main() -> None:
    try:
        from pynput import keyboard
    except ImportError:
        sys.exit("pynput fehlt. Führe 'uv sync --extra jarvis' aus.")

    voice = Voice()
    knowledge = Knowledge(GRAPH_PATH)

    stop_recording = threading.Event()
    is_recording = threading.Event()

    def _handle() -> None:
        audio = voice.record(stop_recording)
        is_recording.clear()

        if audio is None or len(audio) < MIN_AUDIO_SAMPLES:
            print("(Aufnahme zu kurz, ignoriert)")
            return

        print("◎ Transkribiere...")
        text = voice.transcribe(audio)
        if not text.strip():
            print("(Nichts erkannt)")
            return

        print(f"Du:     {text}")
        response = route(text, knowledge)
        print(f"Jarvis: {response}")
        voice.speak(response)

    def on_press(key: keyboard.Key) -> None:
        if key == keyboard.Key.f9 and not is_recording.is_set():
            is_recording.set()
            stop_recording.clear()
            print("\n● Aufnahme läuft... (F9 loslassen zum Senden)")
            threading.Thread(target=_handle, daemon=True).start()

    def on_release(key: keyboard.Key) -> None:
        if key == keyboard.Key.f9:
            stop_recording.set()

    print("Jarvis bereit. F9 halten zum Sprechen. Ctrl+C zum Beenden.\n")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\nJarvis beendet.")


if __name__ == "__main__":
    main()
