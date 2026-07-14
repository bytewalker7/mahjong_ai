"""Read-only central turn indicator driven by public Observation state."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...state.models import PlayerPosition


class TurnIndicatorWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent); self.current = PlayerPosition.SELF; self.dealer = PlayerPosition.SELF; self.wall = 0; self.waiting_response = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_state(self, current: PlayerPosition, dealer: PlayerPosition, wall: int, waiting_response: bool) -> None:
        self.current, self.dealer, self.wall, self.waiting_response = current, dealer, wall, waiting_response; self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = min(self.width(), self.height()); radius = size * .43; center = self.rect().center()
        painter.setBrush(QColor("#152b35")); painter.setPen(QPen(QColor("#b78943"), 3)); painter.drawEllipse(center, radius, radius)
        locations = {PlayerPosition.OPPOSITE: (0, -radius*.69), PlayerPosition.RIGHT: (radius*.69, 0), PlayerPosition.SELF: (0, radius*.69), PlayerPosition.LEFT: (-radius*.69, 0)}
        labels = {PlayerPosition.SELF: "自己", PlayerPosition.LEFT: "上", PlayerPosition.OPPOSITE: "对", PlayerPosition.RIGHT: "下"}
        for position, (dx, dy) in locations.items():
            active = position is self.current
            painter.setBrush(QColor("#25c6b3") if active else QColor("#293d45")); painter.setPen(QPen(QColor("#d9f7ed") if active else QColor("#60747b"), 2))
            painter.drawEllipse(center.x()+dx-15, center.y()+dy-15, 30, 30)
            painter.setPen(QColor("#fff8dc")); painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold)); painter.drawText(center.x()+dx-15, center.y()+dy-15, 30, 30, Qt.AlignmentFlag.AlignCenter, labels[position])
            if position is self.dealer:
                painter.setPen(QColor("#f7c948")); painter.setFont(QFont("Microsoft YaHei", 8, QFont.Weight.Bold)); painter.drawText(center.x()+dx-12, center.y()+dy-31, 24, 14, Qt.AlignmentFlag.AlignCenter, "庄")
        painter.setBrush(QColor("#061b24")); painter.setPen(QPen(QColor("#5de0d0"), 2)); painter.drawRoundedRect(center.x()-33, center.y()-24, 66, 48, 8, 8)
        painter.setPen(QColor("#78fff0")); painter.setFont(QFont("Consolas", 18, QFont.Weight.Bold)); painter.drawText(center.x()-33, center.y()-18, 66, 27, Qt.AlignmentFlag.AlignCenter, str(self.wall))
        painter.setPen(QColor("#e6fbff")); painter.setFont(QFont("Microsoft YaHei", 8)); painter.drawText(center.x()-33, center.y()+6, 66, 16, Qt.AlignmentFlag.AlignCenter, "等待响应" if self.waiting_response else "剩余牌")
