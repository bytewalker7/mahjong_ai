"""Reusable painted Mahjong tile faces and tile-back buttons."""

from __future__ import annotations

from PySide6.QtCore import Property, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from ...tiles import code_to_tile


def _circle(painter: QPainter, x: float, y: float, radius: float, color: QColor) -> None:
    painter.setPen(QPen(QColor("#23455b"), max(1.0, radius * 0.13)))
    painter.setBrush(color)
    painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2, radius * 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#f7fafc"), max(1.0, radius * 0.12)))
    painter.drawEllipse(QRectF(x - radius * .45, y - radius * .45, radius * .9, radius * .9))


def _paint_face(painter: QPainter, rect: QRectF, tile: int) -> None:
    suit, rank = divmod(tile, 9)
    cx, cy = rect.center().x(), rect.center().y()
    if suit == 0:
        painter.setPen(QColor("#9b1c1c"))
        font = QFont("Microsoft YaHei", max(10, int(rect.width() * .42)), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(rect.left(), rect.top() + rect.height() * .10, rect.width(), rect.height() * .45), Qt.AlignmentFlag.AlignCenter, str(rank + 1))
        font.setPointSize(max(9, int(rect.width() * .34))); painter.setFont(font)
        painter.drawText(QRectF(rect.left(), rect.top() + rect.height() * .52, rect.width(), rect.height() * .34), Qt.AlignmentFlag.AlignCenter, "万")
    elif suit == 1:
        painter.setPen(QPen(QColor("#167a46"), max(1, rect.width() * .07)))
        rows = 3 if rank >= 5 else 2
        columns = 2 if rank >= 3 else 1
        total = rank + 1
        for index in range(total):
            col, row = index % columns, index // columns
            x = rect.left() + rect.width() * (.34 + col * .32)
            y = rect.top() + rect.height() * (.22 + row * (.56 / max(1, rows - 1)))
            painter.drawLine(x, y - rect.height() * .10, x, y + rect.height() * .10)
            painter.drawEllipse(QRectF(x - rect.width() * .08, y - rect.height() * .04, rect.width() * .16, rect.height() * .08))
    else:
        colors = (QColor("#167a46"), QColor("#b3262d"), QColor("#24558d"))
        total = rank + 1
        columns = 2 if total <= 4 else 3
        for index in range(total):
            col, row = index % columns, index // columns
            x = rect.left() + rect.width() * (.23 + col * (.54 / max(1, columns - 1)))
            y = rect.top() + rect.height() * (.22 + row * .28)
            _circle(painter, x, y, min(rect.width(), rect.height()) * .105, colors[index % 3])


def paint_tile(painter: QPainter, rect: QRectF, tile: int | None = None, *, face_down: bool = False, selected: bool = False, muted: bool = False) -> None:
    """Paint one physical-looking tile without storing any game state."""
    painter.save()
    if selected:
        painter.translate(0, -min(18, rect.height() * .25))
    shadow = rect.translated(0, max(2, rect.height() * .06))
    painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(0, 0, 0, 75)); painter.drawRoundedRect(shadow, rect.width() * .12, rect.width() * .12)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    if face_down:
        gradient.setColorAt(0, QColor("#159a68")); gradient.setColorAt(1, QColor("#07543e"))
    else:
        gradient.setColorAt(0, QColor("#ffffff")); gradient.setColorAt(1, QColor("#dce5e8"))
    painter.setBrush(gradient); painter.setPen(QPen(QColor("#27505a"), max(1.0, rect.width() * .04)))
    painter.drawRoundedRect(rect, rect.width() * .12, rect.width() * .12)
    inner = rect.adjusted(rect.width() * .11, rect.height() * .08, -rect.width() * .11, -rect.height() * .10)
    if face_down:
        painter.setPen(QPen(QColor("#b3e7ca"), max(1.0, rect.width() * .035)))
        for offset in range(-2, 4):
            painter.drawLine(inner.left(), inner.top() + offset * rect.height() * .16, inner.right(), inner.top() + (offset + 2) * rect.height() * .16)
    elif tile is not None:
        _paint_face(painter, inner, tile)
    if muted:
        painter.setBrush(QColor(20, 30, 35, 125)); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(rect, rect.width() * .12, rect.width() * .12)
    if selected:
        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor("#f5c451"), max(2.0, rect.width() * .07))); painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), rect.width() * .12, rect.width() * .12)
    painter.restore()


class TileWidget(QAbstractButton):
    """Clickable human tile; selection changes only visual lift, never game state."""

    def __init__(self, tile: int, parent=None) -> None:
        super().__init__(parent)
        self.tile = tile; self._selected = False; self._enabled_tile = False
        self.setToolTip(code_to_tile(tile)); self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_tile_enabled(self, enabled: bool) -> None:
        self._enabled_tile = enabled; self.setEnabled(enabled); self.update()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected; self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_tile(painter, QRectF(3, 3, self.width() - 7, self.height() - 8), self.tile, selected=self._selected, muted=not self._enabled_tile)
