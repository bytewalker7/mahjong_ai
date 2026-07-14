"""Standalone static review window for the Mahjong tile art.

Run with ``python -m mahjong_ai.ui.tile_preview``.  It intentionally has no
GameSession, environment, AI, wall, or game-state dependency.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from .widgets.opponent_hand import OpponentHandWidget
from .widgets.tile_widget import TileWidget


class TileArtPreview(QWidget):
    """A fixed artboard: 14 faces below and three 13-tile standing hands."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("麻将牌素材静态预览")
        self.resize(1280, 800)
        self.setMinimumSize(1000, 640)
        self.top_hand = OpponentHandWidget(13, "top", self)
        self.left_hand = OpponentHandWidget(13, "left", self)
        self.right_hand = OpponentHandWidget(13, "right", self)
        # A varied, fixed 14-tile face sample: no game data is used here.
        self.face_tiles = [TileWidget(tile, self) for tile in (0, 1, 2, 4, 6, 9, 10, 12, 14, 18, 20, 22, 24, 26)]
        for tile in self.face_tiles:
            tile.set_tile_enabled(False)
        self._layout_art()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_art()

    def _layout_art(self) -> None:
        width, height = self.width(), self.height()
        hand_width = self.top_hand.hand_width
        self.top_hand.setGeometry((width - hand_width) // 2, 90, hand_width, 34)
        self.left_hand.setGeometry(80, (height - hand_width) // 2 - 15, 34, hand_width)
        self.right_hand.setGeometry(width - 114, (height - hand_width) // 2 - 15, 34, hand_width)
        tile_width = min(68, max(48, (width - 260) // len(self.face_tiles)))
        tile_height = int(tile_width * 1.34)
        gap = 3
        total = len(self.face_tiles) * (tile_width + gap) - gap
        x = (width - total) // 2
        y = height - tile_height - 38
        for tile in self.face_tiles:
            tile.setGeometry(x, y, tile_width, tile_height)
            x += tile_width + gap

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        painter.fillRect(rect, QColor("#2c170e"))
        table = rect.adjusted(35, 30, -35, -30)
        gradient = QLinearGradient(table.topLeft(), table.bottomRight())
        gradient.setColorAt(0, QColor("#14757a"))
        gradient.setColorAt(1, QColor("#084651"))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#a76539"), 12))
        painter.drawRoundedRect(table, 30, 30)
        painter.setPen(QPen(QColor(137, 245, 229, 28), 1))
        for x in range(int(table.left()), int(table.right()), 24):
            painter.drawLine(x, table.top(), x, table.bottom())
        for y in range(int(table.top()), int(table.bottom()), 24):
            painter.drawLine(table.left(), y, table.right(), y)
        painter.setPen(QColor("#d7f8ef"))
        painter.drawText(QRectF(table.center().x() - 170, 45, 340, 28), Qt.AlignmentFlag.AlignCenter, "静态素材预览：站立牌背与正面牌")
        painter.drawText(QRectF(table.center().x() - 120, table.bottom() - 165, 240, 25), Qt.AlignmentFlag.AlignCenter, "人类玩家：完整正面牌")


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = TileArtPreview()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
