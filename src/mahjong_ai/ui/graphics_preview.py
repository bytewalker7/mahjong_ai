"""Static QGraphicsView preview using the supplied table background.

This module deliberately contains no game state.  It demonstrates the final
sprite layering approach before the scene is connected to GameController.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
)


_PACKAGE_ROOT = Path(__file__).parents[1]
_UI_ASSETS = _PACKAGE_ROOT / "assets" / "ui"
_TILE_ASSETS = _PACKAGE_ROOT / "assets" / "tiles"
_SCENE_WIDTH = 1680
_SCENE_HEIGHT = 973


class MahjongGraphicsScene(QGraphicsScene):
    """Layered, static Mahjong table art in the background's native space."""

    def __init__(self) -> None:
        super().__init__(0, 0, _SCENE_WIDTH, _SCENE_HEIGHT)
        self._add_background()
        self._add_concealed_hands()
        self._add_discard_rivers()
        self._add_turn_dial()
        self._add_human_hand_and_melds()

    def _add_background(self) -> None:
        pixmap = QPixmap(str(_UI_ASSETS / "background.png"))
        background = self.addPixmap(pixmap)
        background.setZValue(-100)

    def _add_concealed_hands(self) -> None:
        left = QGraphicsSvgItem(str(_UI_ASSETS / "tile_back_left.svg"))
        left.setPos(330, 122)
        left.setScale(0.88)
        left.setZValue(20)
        self.addItem(left)

        right = QGraphicsSvgItem(str(_UI_ASSETS / "tile_back_right.svg"))
        right.setPos(1182, 122)
        right.setScale(0.88)
        right.setZValue(20)
        self.addItem(right)

        sprite = QPixmap(str(_UI_ASSETS / "tile_back_3d.png"))
        tile = sprite.scaled(43, 76, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        for index in range(13):
            item = QGraphicsPixmapItem(tile)
            item.setPos(575 + index * 37, 68)
            item.setZValue(20 + index * 0.01)
            self.addItem(item)

    def _face_item(self, code: str, width: float, height: float) -> QGraphicsItemGroup:
        group = QGraphicsItemGroup()
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(QRectF(3, 5, width, height), 5, 5)
        shadow = QGraphicsPathItem(shadow_path, group)
        shadow.setBrush(QColor(0, 0, 0, 105))
        shadow.setPen(Qt.PenStyle.NoPen)

        body_path = QPainterPath()
        body_path.addRoundedRect(QRectF(0, 0, width, height), 5, 5)
        body = QGraphicsPathItem(body_path, group)
        body.setBrush(QColor("#fffdf4"))
        body.setPen(QPen(QColor("#52666a"), 1.3))

        face = QGraphicsSvgItem(str(_TILE_ASSETS / f"{code}.svg"), group)
        bounds = face.boundingRect()
        scale = min((width - 5) / bounds.width(), (height - 6) / bounds.height())
        face.setScale(scale)
        face.setPos((width - bounds.width() * scale) / 2, (height - bounds.height() * scale) / 2 - 1)
        return group

    def _add_river(self, codes: list[str], x: float, y: float, columns: int, rotation: float) -> None:
        group = QGraphicsItemGroup()
        self.addItem(group)
        tile_width, tile_height, gap = 33, 45, 2
        for index, code in enumerate(codes):
            item = self._face_item(code, tile_width, tile_height)
            item.setParentItem(group)
            item.setPos((index % columns) * (tile_width + gap), (index // columns) * (tile_height + gap))
        bounds = group.childrenBoundingRect()
        group.setTransformOriginPoint(bounds.center())
        group.setRotation(rotation)
        group.setPos(x - bounds.width() / 2, y - bounds.height() / 2)
        group.setZValue(10)

    def _add_discard_rivers(self) -> None:
        self._add_river(["2s", "4p", "7w", "6p", "8p", "5s", "3s", "1s", "5w", "2p", "9w", "1p"], 840, 245, 6, 180)
        self._add_river(["2w", "5w", "7w", "3p", "1p", "9w", "8w", "6s", "5p", "2s", "1s"], 555, 472, 6, 90)
        self._add_river(["1p", "9w", "7w", "4p", "3s", "1s", "2w", "5s", "8p", "6p", "1w"], 1125, 472, 6, -90)
        self._add_river(["6w", "5w", "1s", "1p", "5p", "7w", "1w", "7w", "5p", "8p", "1w", "2p", "6p", "9w"], 840, 687, 8, 0)

    def _add_turn_dial(self) -> None:
        outer = QGraphicsEllipseItem(QRectF(735, 360, 210, 180))
        outer.setBrush(QColor("#b225292d"))
        outer.setPen(QPen(QColor("#a77740"), 4))
        outer.setZValue(12)
        self.addItem(outer)
        positions = ((818, 368), (744, 430), (892, 430), (818, 492))
        labels = ("N", "W", "E", "S")
        for index, ((x, y), label) in enumerate(zip(positions, labels, strict=True)):
            light = QGraphicsEllipseItem(QRectF(x, y, 44, 34))
            light.setBrush(QColor("#9f382b") if index == 3 else QColor("#343a3d"))
            light.setPen(QPen(QColor("#f2c35b") if index == 3 else QColor("#687176"), 2))
            light.setZValue(13)
            self.addItem(light)
            text = QGraphicsTextItem(label)
            text.setDefaultTextColor(QColor("#f4ead7"))
            text.setPos(x + 11, y + 3)
            text.setZValue(14)
            self.addItem(text)
        counter = QGraphicsTextItem("31")
        counter.setDefaultTextColor(QColor("#55f3ed"))
        font = counter.font()
        font.setPointSize(25)
        font.setBold(True)
        counter.setFont(font)
        counter.setPos(815, 420)
        counter.setZValue(15)
        self.addItem(counter)

    def _add_human_hand_and_melds(self) -> None:
        codes = ["4s", "5s", "6s", "7s", "8s", "4p", "5p", "7p", "2p"]
        x = 277
        for code in codes:
            tile = self._face_item(code, 62, 86)
            tile.setPos(x, 842)
            tile.setZValue(30)
            self.addItem(tile)
            x += 64
        meld_x = 1190
        for code in ["9p", "9p", "9p", "6s", "6s", "6s"]:
            tile = self._face_item(code, 47, 65)
            tile.setPos(meld_x, 852)
            tile.setZValue(30)
            self.addItem(tile)
            meld_x += 49


class MahjongGraphicsPreview(QGraphicsView):
    """Responsive view; scene coordinates remain stable for later animation."""

    def __init__(self) -> None:
        super().__init__()
        self._mahjong_scene = MahjongGraphicsScene()
        self.setScene(self._mahjong_scene)
        self.setWindowTitle("麻将桌 QGraphicsView 静态预览")
        self.resize(1400, 820)
        self.setMinimumSize(1000, 600)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#160b07"))
        self._fit_scene()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_scene()

    def _fit_scene(self) -> None:
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    view = MahjongGraphicsPreview()
    view.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
