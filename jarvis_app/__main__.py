"""Jarvis — Windows Desktop Assistent. Starten: python -m jarvis_app"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from jarvis_app.ui.app import JarvisApp


def main() -> None:
    # Ensure high-DPI is handled correctly on Windows
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Jarvis")
    app.setOrganizationName("Jarvis")
    app.setQuitOnLastWindowClosed(False)  # keep running in tray

    jarvis = JarvisApp(app)
    sys.exit(jarvis.run())


if __name__ == "__main__":
    main()
