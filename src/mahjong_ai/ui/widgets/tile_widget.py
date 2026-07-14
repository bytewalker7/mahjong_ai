"""Mahjong tile widgets backed by the bundled SVG face artwork."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton

from ...tiles import code_to_tile


_ASSET_DIRECTORY = Path(__file__).parents[2] / "assets" / "tiles"
_SUITS = ("w", "s", "p")


def tile_svg_path(tile: int) -> Path:
    """Return the public SVG face associated with a 0--26 tile code."""
    suit, rank = divmod(tile, 9)
    return _ASSET_DIRECTORY / f"{rank + 1}{_SUITS[suit]}.svg"


@lru_cache(maxsize=27)
def _face_renderer(tile: int) -> QSvgRenderer:
    return QSvgRenderer(str(tile_svg_path(tile)))


@lru_cache(maxsize=1)
def _standing_back_renderer() -> QSvgRenderer:
    return QSvgRenderer(str(_ASSET_DIRECTORY / "tile_back_standing.svg"))


def paint_face_tile(
    painter: QPainter,
    rect: QRectF,
    tile: int,
    *,
    selected: bool = False,
    muted: bool = False,
) -> None:
    """Paint a bundled face SVG with only a small UI shadow/selection frame."""
    painter.save()
    if selected:
        painter.translate(0, -min(18.0, rect.height() * 0.20))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 82))
    painter.drawRoundedRect(rect.translated(0, max(2.0, rect.height() * 0.045)), 5, 5)
    renderer = _face_renderer(tile)
    if renderer.isValid():
        renderer.render(painter, rect)
    else:
        painter.setPen(QColor("#b61f29"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, code_to_tile(tile))
    if muted:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(14, 31, 35, 105))
        painter.drawRoundedRect(rect, 5, 5)
    if selected:
        painter.setPen(QPen(QColor("#f7c948"), max(2.0, rect.width() * 0.055)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 5, 5)
    painter.restore()


def paint_standing_back(painter: QPainter, rect: QRectF) -> None:
    """Paint the pre-rendered 2.5D standing back; never a rotated face tile."""
    renderer = _standing_back_renderer()
    if renderer.isValid():
        renderer.render(painter, rect)


def paint_tile(
    painter: QPainter,
    rect: QRectF,
    tile: int | None = None,
    *,
    face_down: bool = False,
    selected: bool = False,
    muted: bool = False,
) -> None:
    """Compatibility painter for the existing table widget.

    The forthcoming opponent-hand integration replaces its face-down branch
    with :func:`paint_standing_back`.  This safe flat fallback keeps the
    currently playable window importable while the static art is reviewed.
    """
    if not face_down and tile is not None:
        paint_face_tile(painter, rect, tile, selected=selected, muted=muted)
        return
    painter.save()
    painter.setPen(QPen(QColor("#064c30"), max(1.0, rect.width() * .04)))
    painter.setBrush(QColor("#12834c"))
    painter.drawRoundedRect(rect, 5, 5)
    painter.restore()


class TileWidget(QAbstractButton):
    """A clickable, SVG-backed human hand tile; it contains no game state."""

    def __init__(self, tile: int, parent=None) -> None:
        super().__init__(parent)
        self.tile = tile
        self._selected = False
        self._enabled_tile = False
        self.setToolTip(code_to_tile(tile))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_tile_enabled(self, enabled: bool) -> None:
        self._enabled_tile = enabled
        self.setEnabled(enabled)
        self.update()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_face_tile(
            painter,
            QRectF(3, 3, self.width() - 7, self.height() - 8),
            self.tile,
            selected=self._selected,
        )
