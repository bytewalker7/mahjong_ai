<<<<<<< ours
<<<<<<< ours
"""Reusable painted Mahjong tile faces and tile-back buttons."""

from __future__ import annotations

from PySide6.QtCore import Property, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
=======
=======
>>>>>>> theirs
"""Traditional three-suit Mahjong tile painting, drawn entirely in Qt."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
from PySide6.QtWidgets import QAbstractButton

from ...tiles import code_to_tile


<<<<<<< ours
<<<<<<< ours
def _circle(painter: QPainter, x: float, y: float, radius: float, color: QColor) -> None:
    painter.setPen(QPen(QColor("#23455b"), max(1.0, radius * 0.13)))
    painter.setBrush(color)
    painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2, radius * 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#f7fafc"), max(1.0, radius * 0.12)))
    painter.drawEllipse(QRectF(x - radius * .45, y - radius * .45, radius * .9, radius * .9))
=======
=======
>>>>>>> theirs
_CHINESE_NUMBERS = ("\u4e00", "\u4e8c", "\u4e09", "\u56db", "\u4e94", "\u516d", "\u4e03", "\u516b", "\u4e5d")
_PIP_LAYOUTS = {
    1: ((.50, .50),),
    2: ((.50, .25), (.50, .75)),
    3: ((.50, .20), (.50, .50), (.50, .80)),
    4: ((.28, .25), (.72, .25), (.28, .75), (.72, .75)),
    5: ((.28, .25), (.72, .25), (.50, .50), (.28, .75), (.72, .75)),
    6: ((.27, .20), (.73, .20), (.27, .50), (.73, .50), (.27, .80), (.73, .80)),
    7: ((.50, .16), (.27, .32), (.73, .32), (.27, .54), (.73, .54), (.27, .78), (.73, .78)),
    8: ((.27, .16), (.73, .16), (.27, .38), (.73, .38), (.27, .62), (.73, .62), (.27, .84), (.73, .84)),
    9: ((.27, .18), (.50, .18), (.73, .18), (.27, .50), (.50, .50), (.73, .50), (.27, .82), (.50, .82), (.73, .82)),
}


def _pip(painter: QPainter, x: float, y: float, radius: float, color: QColor) -> None:
    painter.setPen(QPen(QColor("#102d3b"), max(0.8, radius * .18)))
    painter.setBrush(color)
    painter.drawEllipse(QRectF(x-radius, y-radius, radius*2, radius*2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#fffdf4"), max(.7, radius*.16)))
    painter.drawEllipse(QRectF(x-radius*.48, y-radius*.48, radius*.96, radius*.96))


def _bamboo(painter: QPainter, x: float, y: float, width: float, height: float) -> None:
    painter.setPen(QPen(QColor("#0c5d38"), max(1.0, width*.12)))
    painter.setBrush(QColor("#218a50"))
    painter.drawRoundedRect(QRectF(x-width*.22, y-height*.48, width*.44, height*.96), width*.22, width*.22)
    painter.setPen(QPen(QColor("#d9f7bf"), max(.7, width*.07)))
    for ratio in (.25, .50, .75):
        painter.drawLine(x-width*.18, y-height*.5+height*ratio, x+width*.18, y-height*.5+height*ratio)


def _one_bamboo(painter: QPainter, rect: QRectF) -> None:
    """A compact, original bird-like green one-bamboo motif."""
    cx, cy = rect.center().x(), rect.center().y()
    painter.setPen(QPen(QColor("#0f6336"), max(1.3, rect.width()*.065)))
    painter.setBrush(QColor("#2b9652"))
    body = QPainterPath(); body.moveTo(cx, cy-rect.height()*.29); body.cubicTo(cx+rect.width()*.23, cy-rect.height()*.12, cx+rect.width()*.16, cy+rect.height()*.21, cx, cy+rect.height()*.30); body.cubicTo(cx-rect.width()*.15, cy+rect.height()*.12, cx-rect.width()*.18, cy-rect.height()*.02, cx, cy-rect.height()*.29)
    painter.drawPath(body)
    painter.setBrush(QColor("#eae4b6")); painter.drawEllipse(QRectF(cx-rect.width()*.06, cy-rect.height()*.22, rect.width()*.12, rect.height()*.12))
    painter.setBrush(QColor("#bf3335")); painter.setPen(Qt.PenStyle.NoPen); painter.drawEllipse(QRectF(cx+rect.width()*.025, cy-rect.height()*.18, rect.width()*.025, rect.width()*.025))
    painter.setPen(QPen(QColor("#0f6336"), max(1, rect.width()*.045)))
    painter.drawLine(cx-rect.width()*.20, cy+rect.height()*.23, cx-rect.width()*.34, cy+rect.height()*.37)
    painter.drawLine(cx+rect.width()*.13, cy+rect.height()*.19, cx+rect.width()*.30, cy+rect.height()*.34)


def _paint_wan(painter: QPainter, rect: QRectF, rank: int) -> None:
    painter.setPen(QColor("#17242a")); painter.setFont(QFont("Microsoft YaHei", max(9, int(rect.width()*.48)), QFont.Weight.Bold))
    painter.drawText(QRectF(rect.left(), rect.top()+rect.height()*.08, rect.width(), rect.height()*.40), Qt.AlignmentFlag.AlignCenter, _CHINESE_NUMBERS[rank])
    painter.setPen(QColor("#b01925")); painter.setFont(QFont("STKaiti", max(11, int(rect.width()*.53)), QFont.Weight.Bold))
    painter.drawText(QRectF(rect.left(), rect.top()+rect.height()*.50, rect.width(), rect.height()*.37), Qt.AlignmentFlag.AlignCenter, "\u4e07")


def _paint_bamboo(painter: QPainter, rect: QRectF, rank: int) -> None:
    if rank == 0:
        _one_bamboo(painter, rect); return
    layout = _PIP_LAYOUTS[rank+1]
    for x_ratio, y_ratio in layout:
        _bamboo(painter, rect.left()+rect.width()*x_ratio, rect.top()+rect.height()*y_ratio, rect.width()*.26, rect.height()*.19)


def _paint_dots(painter: QPainter, rect: QRectF, rank: int) -> None:
    colors = (QColor("#19834c"), QColor("#bf3034"), QColor("#1d5793"))
    for index, (x_ratio, y_ratio) in enumerate(_PIP_LAYOUTS[rank+1]):
        _pip(painter, rect.left()+rect.width()*x_ratio, rect.top()+rect.height()*y_ratio, min(rect.width(), rect.height())*.105, colors[index % len(colors)])
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs


def _paint_face(painter: QPainter, rect: QRectF, tile: int) -> None:
    suit, rank = divmod(tile, 9)
<<<<<<< ours
<<<<<<< ours
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
=======
=======
>>>>>>> theirs
    if suit == 0: _paint_wan(painter, rect, rank)
    elif suit == 1: _paint_bamboo(painter, rect, rank)
    else: _paint_dots(painter, rect, rank)


def _paint_back(painter: QPainter, rect: QRectF) -> None:
    panel = rect.adjusted(rect.width()*.11, rect.height()*.10, -rect.width()*.11, -rect.height()*.12)
    gradient = QLinearGradient(panel.topLeft(), panel.bottomRight()); gradient.setColorAt(0, QColor("#36b76d")); gradient.setColorAt(1, QColor("#07633d"))
    painter.setBrush(gradient); painter.setPen(QPen(QColor("#d7f4bd"), max(1., rect.width()*.035))); painter.drawRoundedRect(panel, rect.width()*.06, rect.width()*.06)
    painter.setPen(QPen(QColor("#b9f2bf"), max(.8, rect.width()*.032)))
    spacing = max(4., rect.width()*.22)
    x = panel.left()-panel.height()
    while x < panel.right():
        painter.drawLine(x, panel.bottom(), x+panel.height(), panel.top()); x += spacing
    painter.setPen(QPen(QColor("#063b2a"), max(1., rect.width()*.04))); painter.setBrush(Qt.BrushStyle.NoBrush); painter.drawRoundedRect(panel.adjusted(2,2,-2,-2), rect.width()*.05, rect.width()*.05)


def paint_tile(painter: QPainter, rect: QRectF, tile: int | None = None, *, face_down: bool = False, selected: bool = False, muted: bool = False) -> None:
    """Paint an ivory tile with a dark lower side, bevel, face or green back."""
    painter.save()
    if selected: painter.translate(0, -min(18, rect.height()*.25))
    shadow = rect.translated(0, max(2., rect.height()*.075))
    painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(0, 0, 0, 92)); painter.drawRoundedRect(shadow, rect.width()*.12, rect.width()*.12)
    side = rect.translated(0, max(2., rect.height()*.065))
    painter.setBrush(QColor("#9eaeb0")); painter.setPen(QPen(QColor("#47606a"), max(1., rect.width()*.035))); painter.drawRoundedRect(side, rect.width()*.11, rect.width()*.11)
    face_gradient = QLinearGradient(rect.topLeft(), rect.bottomRight()); face_gradient.setColorAt(0, QColor("#fffef6")); face_gradient.setColorAt(.72, QColor("#f5f2e5")); face_gradient.setColorAt(1, QColor("#d7dfd9"))
    painter.setBrush(face_gradient); painter.setPen(QPen(QColor("#35525a"), max(1., rect.width()*.04))); painter.drawRoundedRect(rect, rect.width()*.11, rect.width()*.11)
    inner = rect.adjusted(rect.width()*.105, rect.height()*.075, -rect.width()*.105, -rect.height()*.105)
    painter.setPen(QPen(QColor(255,255,255,180), max(1., rect.width()*.026))); painter.setBrush(Qt.BrushStyle.NoBrush); painter.drawRoundedRect(inner, rect.width()*.06, rect.width()*.06)
    if face_down: _paint_back(painter, rect)
    elif tile is not None: _paint_face(painter, inner, tile)
    if muted:
        painter.setBrush(QColor(18, 30, 32, 92)); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(rect, rect.width()*.11, rect.width()*.11)
    if selected:
        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor("#f7c948"), max(2., rect.width()*.06))); painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), rect.width()*.11, rect.width()*.11)
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
    painter.restore()


class TileWidget(QAbstractButton):
<<<<<<< ours
<<<<<<< ours
    """Clickable human tile; selection changes only visual lift, never game state."""

    def __init__(self, tile: int, parent=None) -> None:
        super().__init__(parent)
        self.tile = tile; self._selected = False; self._enabled_tile = False
=======
=======
>>>>>>> theirs
    """Clickable human tile; disabled tiles remain readable rather than greyed out."""

    def __init__(self, tile: int, parent=None) -> None:
        super().__init__(parent); self.tile = tile; self._selected = False; self._enabled_tile = False
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
        self.setToolTip(code_to_tile(tile)); self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_tile_enabled(self, enabled: bool) -> None:
        self._enabled_tile = enabled; self.setEnabled(enabled); self.update()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected; self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
<<<<<<< ours
<<<<<<< ours
        paint_tile(painter, QRectF(3, 3, self.width() - 7, self.height() - 8), self.tile, selected=self._selected, muted=not self._enabled_tile)
=======
        paint_tile(painter, QRectF(3,3,self.width()-7,self.height()-8), self.tile, selected=self._selected)
>>>>>>> theirs
=======
        paint_tile(painter, QRectF(3,3,self.width()-7,self.height()-8), self.tile, selected=self._selected)
>>>>>>> theirs
