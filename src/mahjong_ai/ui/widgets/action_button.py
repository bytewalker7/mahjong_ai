"""Large round legal-action buttons for the human seat."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QAbstractButton


class RoundActionButton(QAbstractButton):
    COLORS = {"胡": ("#e95a3d", "#7f1d1d"), "碰": ("#f2b134", "#9a5c09"), "杠": ("#e48828", "#8a3e08"), "过": ("#2a9dc6", "#14516b")}

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent); self.setText(text); self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(5, 5, -5, -5); light, dark = self.COLORS.get(self.text()[0], ("#64748b", "#334155"))
        gradient = QRadialGradient(rect.center(), rect.width()*.55); gradient.setColorAt(0, QColor(light)); gradient.setColorAt(1, QColor(dark))
        painter.setBrush(gradient); painter.setPen(QPen(QColor("#fff1b8"), 2 if self.isDown() else 3)); painter.drawEllipse(rect)
        painter.setPen(QColor("#ffffff")); painter.setFont(QFont("Microsoft YaHei", max(15, rect.width()//4), QFont.Weight.Bold)); painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
