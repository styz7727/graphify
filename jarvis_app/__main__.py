"""Jarvis — Windows Desktop Assistent. Starten: python -m jarvis_app"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from jarvis_app.ui.app import JarvisApp

# Windows error code returned by CreateMutexW when the mutex already exists
_ERROR_ALREADY_EXISTS = 183
_MUTEX_NAME = "JarvisV6_SingleInstance_Mutex"
_mutex_handle = None   # keep reference so it isn't GC'd while the app runs


def _acquire_single_instance() -> bool:
    """Create a named Windows mutex. Returns False if another instance is running."""
    global _mutex_handle
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        _mutex_handle = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        if kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
            return False
        return True
    except Exception:
        return True   # if we can't check, allow startup


def _warn_already_running(app: QApplication) -> None:
    msg = QMessageBox()
    msg.setWindowTitle("Jarvis läuft bereits")
    msg.setText(
        "Eine Instanz von Jarvis ist bereits aktiv.\n\n"
        "Schau in der Taskleiste (System Tray) nach dem 🤖-Icon.\n"
        "Starte Jarvis nicht mehrfach — das führt zu doppelter Sprachausgabe."
    )
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Jarvis")
    app.setOrganizationName("Jarvis")
    app.setQuitOnLastWindowClosed(False)

    if not _acquire_single_instance():
        _warn_already_running(app)
        sys.exit(0)

    jarvis = JarvisApp(app)
    sys.exit(jarvis.run())


if __name__ == "__main__":
    main()
