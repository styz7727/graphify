"""Qt confirmation dialog for CONFIRM-level actions."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QHBoxLayout, QPushButton, QVBoxLayout


class ConfirmationDialog(QDialog):
    """Modal dialog: shows action description, returns True if user approved."""

    def __init__(self, description: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("⚠ Bestätigung erforderlich")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumWidth(380)
        self.confirmed = False
        self._build_ui(description)
        self.setStyleSheet(_STYLE)

    def _build_ui(self, description: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        icon_label = QLabel("⚠")
        icon_label.setStyleSheet("font-size: 28px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title = QLabel("Soll ich das wirklich ausführen?")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e0e0e0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #a0c4ff; background: #0f3460; "
                           "border-radius: 6px; padding: 8px 12px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        btns = QHBoxLayout()
        btns.setSpacing(12)

        yes = QPushButton("✓  Ja, ausführen")
        yes.setStyleSheet("background:#4ecca3; color:#1a1a2e; font-weight:bold; "
                          "border-radius:6px; padding:8px 18px;")
        yes.clicked.connect(self._accept)

        no = QPushButton("✗  Abbrechen")
        no.setStyleSheet("background:#e94560; color:#fff; font-weight:bold; "
                         "border-radius:6px; padding:8px 18px;")
        no.clicked.connect(self._reject)

        btns.addWidget(yes)
        btns.addWidget(no)
        layout.addLayout(btns)

    def _accept(self) -> None:
        self.confirmed = True
        self.accept()

    def _reject(self) -> None:
        self.confirmed = False
        self.reject()


_STYLE = """
QDialog { background-color: #1a1a2e; border: 1px solid #0f3460; border-radius: 10px; }
QLabel  { color: #e0e0e0; }
"""
