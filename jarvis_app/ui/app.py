"""QApplication setup and System Tray Icon."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from jarvis_app.ui.overlay import Overlay


def _make_icon() -> QIcon:
    """Create a simple text-based tray icon without external resources."""
    px = QPixmap(QSize(64, 64))
    px.fill(QColor("transparent"))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#1a1a2e"))
    p.setPen(QColor("#4ecca3"))
    p.drawEllipse(2, 2, 60, 60)
    p.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
    p.setPen(QColor("#4ecca3"))
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "J")
    p.end()
    return QIcon(px)


class JarvisApp:
    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._overlay = Overlay()
        self._tray = self._build_tray()

    def _build_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(_make_icon(), self._app)
        tray.setToolTip("Jarvis")
        tray.activated.connect(self._on_tray_activate)

        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background:#1a1a2e; color:#e0e0e0; border:1px solid #0f3460; }"
            "QMenu::item:selected { background:#0f3460; }"
        )
        menu.addAction("🤖 Jarvis öffnen",    self._overlay.show)
        menu.addAction("🔒 Permission Center", self._show_permissions)
        menu.addSeparator()
        menu.addAction("❌ Beenden",           self._app.quit)

        tray.setContextMenu(menu)
        tray.show()
        return tray

    def _on_tray_activate(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._overlay.isVisible():
                self._overlay.hide()
            else:
                self._overlay.show()
                self._overlay.activateWindow()
                self._overlay.raise_()

    def _show_permissions(self) -> None:
        from jarvis_app.ui.permission_center import PermissionCenter
        dlg = PermissionCenter()
        dlg.exec()

    def run(self) -> int:
        self._overlay.show()
        self._overlay.start_push_to_talk()
        self._overlay.start_wake_word_listener()
        return self._app.exec()
