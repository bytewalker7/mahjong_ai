"""Static 2.5D opponent concealed-hand widgets.

The widget deliberately uses the pre-rendered standing-back asset.  It never
receives tile identities and never draws a face tile.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from .tile_widget import paint_standing_back


class OpponentHandWidget(QWidget):
    """A row of identical standing backs, optionally rotated as one hand."""

    tile_width = 48
    tile_height = 28
    overlap = 2

    def __init__(self, concealed_tile_count: int = 13, direction: str = "top", parent=None) -> None:
        super().__init__(parent)
        if direction not in {"top", "left", "right"}:
            raise ValueError(f"unsupported hand direction: {direction}")
        self.concealed_tile_count = concealed_tile_count
        self.direction = direction
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    @property
    def hand_width(self) -> int:
        return self.concealed_tile_count * (self.tile_width - self.overlap) + self.overlap

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.save()
        if self.direction == "top":
            x, y = (self.width() - self.hand_width) / 2, 0
        else:
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(90 if self.direction == "left" else -90)
            x, y = -self.hand_width / 2, -self.tile_height / 2
        for index in range(self.concealed_tile_count):
            paint_standing_back(
                painter,
                QRectF(x + index * (self.tile_width - self.overlap), y, self.tile_width, self.tile_height),
            )
        painter.restore()
