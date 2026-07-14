"""Responsive bird's-eye Mahjong table rendered only from PublicGameView."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...game.session import PublicGameView
from ...simulator.models import Action, DiscardAction, Phase
from ...state.models import PlayerPosition
from .tile_widget import TileWidget, paint_tile
from .turn_indicator import TurnIndicatorWidget


_NAMES = {PlayerPosition.SELF: "自己", PlayerPosition.LEFT: "上家 AI", PlayerPosition.OPPOSITE: "对家 AI", PlayerPosition.RIGHT: "下家 AI"}
_SHORT = {PlayerPosition.SELF: "自己", PlayerPosition.LEFT: "上家", PlayerPosition.OPPOSITE: "对家", PlayerPosition.RIGHT: "下家"}
_MELD_COUNT = {"peng": 3, "exposed_gang": 4, "concealed_gang": 4, "added_gang": 4}


class MahjongTableWidget(QWidget):
    """A table surface.  It stores no tile facts, only current public render data."""

    tile_clicked = Signal(int)
    empty_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._view: PublicGameView | None = None
        self._legal: tuple[Action, ...] = ()
        self._selected: int | None = None
        self.hand_widgets: list[TileWidget] = []
        self.indicator = TurnIndicatorWidget(self)
        self.setMinimumSize(900, 620)
        self.setAutoFillBackground(False)

    def set_game(self, view: PublicGameView, legal: tuple[Action, ...], selected_tile: int | None) -> None:
        self._view, self._legal, self._selected = view, legal, selected_tile
        self._rebuild_hand(); self._layout_children(); self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event); self._layout_children()

    def mousePressEvent(self, event) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            self.empty_clicked.emit()
        super().mousePressEvent(event)

    def _rebuild_hand(self) -> None:
        for widget in self.hand_widgets:
            widget.deleteLater()
        self.hand_widgets = []
        if self._view is None:
            return
        observation = self._view.observation
        tiles = [tile for tile, count in enumerate(observation.own_hand) for _ in range(count)]
        if self._view.drawn_tile is not None and self._view.drawn_tile in tiles:
            tiles.remove(self._view.drawn_tile); tiles.append(self._view.drawn_tile)
        legal_tiles = {action.tile for action in self._legal if isinstance(action, DiscardAction)}
        for tile in tiles:
            widget = TileWidget(tile, self)
            widget.set_tile_enabled(tile in legal_tiles)
            widget.set_selected(tile == self._selected)
            widget.clicked.connect(lambda _checked=False, value=tile: self.tile_clicked.emit(value))
            widget.show(); self.hand_widgets.append(widget)

    def _layout_children(self) -> None:
        width, height = self.width(), self.height()
        if width <= 0 or height <= 0:
            return
        size = min(58, max(34, int((width - 130) / max(14, len(self.hand_widgets) or 14))))
        tile_h = int(size * 1.36); gap = max(1, int(size * .05))
        drawn_gap = int(size * .34)
        total = len(self.hand_widgets) * (size + gap) - gap + (drawn_gap if self._view and self._view.drawn_tile is not None and self.hand_widgets else 0)
        x, y = (width - total) // 2, height - tile_h - 22
        for index, widget in enumerate(self.hand_widgets):
            if self._view and self._view.drawn_tile is not None and index == len(self.hand_widgets) - 1:
                x += drawn_gap
            widget.setGeometry(x, y, size, tile_h)
            x += size + gap
        indicator_size = min(176, max(110, int(min(width, height) * .22)))
        self.indicator.setGeometry(width//2 - indicator_size//2, height//2 - indicator_size//2 - 16, indicator_size, indicator_size)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        outer = QLinearGradient(rect.topLeft(), rect.bottomRight()); outer.setColorAt(0, QColor("#4d2412")); outer.setColorAt(1, QColor("#1f110c"))
        painter.fillRect(rect, outer)
        board = rect.adjusted(30, 20, -30, -20)
        cloth = QLinearGradient(board.topLeft(), board.bottomRight()); cloth.setColorAt(0, QColor("#116c75")); cloth.setColorAt(.5, QColor("#0b5963")); cloth.setColorAt(1, QColor("#073d4a"))
        painter.setBrush(cloth); painter.setPen(QPen(QColor("#a86438"), 12)); painter.drawRoundedRect(board, 28, 28)
        painter.setPen(QPen(QColor(120, 235, 220, 25), 1))
        for x in range(int(board.left()), int(board.right()), 22): painter.drawLine(x, board.top(), x, board.bottom())
        for y in range(int(board.top()), int(board.bottom()), 22): painter.drawLine(board.left(), y, board.right(), y)
        if self._view is None:
            return
        self._draw_seats(painter, board)
        self._draw_walls(painter, board)
        self._draw_rivers(painter, board)
        self._draw_melds(painter, board)
        view = self._view; observation = view.observation
        waiting = observation.phase is Phase.RESPONSE
        self.indicator.set_state(observation.current_player, view.dealer, observation.wall_remaining, waiting)
        painter.setPen(QColor("#c5f7ef")); painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        message = "等待响应" if waiting else ("请选择弃牌" if observation.current_player is PlayerPosition.SELF and self._legal else f"{_NAMES[observation.current_player]}行动中")
        painter.drawText(QRectF(board.center().x()-150, board.bottom()-150, 300, 30), Qt.AlignmentFlag.AlignCenter, message)

    def _draw_seats(self, painter: QPainter, board: QRectF) -> None:
        assert self._view is not None
        observation = self._view.observation
        locations = {
            PlayerPosition.OPPOSITE: QRectF(board.center().x()-105, board.top()+14, 210, 34),
            PlayerPosition.LEFT: QRectF(board.left()+16, board.center().y()-18, 130, 36),
            PlayerPosition.RIGHT: QRectF(board.right()-146, board.center().y()-18, 130, 36),
            PlayerPosition.SELF: QRectF(board.center().x()-105, board.bottom()-112, 210, 28),
        }
        for position, text_rect in locations.items():
            active = position is observation.current_player and not self._view.finished
            painter.setBrush(QColor("#15333b") if not active else QColor("#146d70")); painter.setPen(QPen(QColor("#75f2dc") if active else QColor("#477079"), 3 if active else 1))
            painter.drawRoundedRect(text_rect, 10, 10)
            score = self._view.final_scores[position] if self._view.final_scores else 0
            dealer = "庄 " if position is self._view.dealer else ""
            text = f"{dealer}{_NAMES[position]}  {score:+d}"
            painter.setPen(QColor("#fff9df")); painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold)); painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        counts = observation.concealed_tile_counts
        self._draw_back_row(painter, board.center().x(), board.top()+58, counts[PlayerPosition.OPPOSITE], horizontal=True)
        self._draw_back_row(painter, board.left()+64, board.center().y(), counts[PlayerPosition.LEFT], horizontal=False)
        self._draw_back_row(painter, board.right()-64, board.center().y(), counts[PlayerPosition.RIGHT], horizontal=False)

    def _draw_back_row(self, painter: QPainter, center_x: float, center_y: float, count: int, *, horizontal: bool) -> None:
        tile_w, tile_h = (20, 34) if horizontal else (34, 20)
        spacing = tile_w * .62 if horizontal else tile_h * .62
        start = (center_x - (count-1)*spacing/2, center_y - tile_h/2) if horizontal else (center_x-tile_w/2, center_y-(count-1)*spacing/2)
        for index in range(count):
            rect = QRectF(start[0] + (index*spacing if horizontal else 0), start[1] + (0 if horizontal else index*spacing), tile_w, tile_h)
            paint_tile(painter, rect, face_down=True)

    def _draw_walls(self, painter: QPainter, board: QRectF) -> None:
        # Decorative wall rails are not a second wall model; only the count is factual.
        for x, y, w, h in ((board.center().x()-145, board.top()+92, 290, 14), (board.center().x()-145, board.bottom()-170, 290, 14), (board.left()+106, board.center().y()-82, 14, 164), (board.right()-120, board.center().y()-82, 14, 164)):
            painter.setBrush(QColor("#0c8b5e")); painter.setPen(QPen(QColor("#b2eac9"), 1)); painter.drawRoundedRect(QRectF(x,y,w,h), 4, 4)

    def _river_specs(self, board: QRectF):
        return {
            PlayerPosition.SELF: (board.center().x()-115, board.bottom()-265, 0),
            PlayerPosition.OPPOSITE: (board.center().x()+115, board.top()+185, 180),
            PlayerPosition.LEFT: (board.left()+205, board.center().y()+105, 90),
            PlayerPosition.RIGHT: (board.right()-205, board.center().y()-105, 270),
        }

    def _draw_rivers(self, painter: QPainter, board: QRectF) -> None:
        assert self._view is not None
        observation = self._view.observation
        for position in PlayerPosition:
            base_x, base_y, rotation = self._river_specs(board)[position]
            records = observation.public_discards[position]
            for index, (tile, used) in enumerate(records):
                col, row = index % 6, index // 6
                center = QPointF(base_x + col*34, base_y + row*43)
                highlight = position is self._view.last_discard_player and index == len(records)-1
                self._paint_rotated_tile(painter, center, 31, 42, tile, rotation, muted=used, highlight=highlight)

    def _draw_melds(self, painter: QPainter, board: QRectF) -> None:
        assert self._view is not None
        observation = self._view.observation
        anchors = {
            PlayerPosition.SELF: (board.right()-290, board.bottom()-125, 0),
            PlayerPosition.OPPOSITE: (board.left()+230, board.top()+115, 180),
            PlayerPosition.LEFT: (board.left()+135, board.bottom()-235, 90),
            PlayerPosition.RIGHT: (board.right()-135, board.top()+235, 270),
        }
        for position in PlayerPosition:
            x, y, rotation = anchors[position]; offset = 0
            for kind, tile in observation.public_melds[position]:
                for index in range(_MELD_COUNT.get(kind, 3)):
                    hidden = kind == "concealed_gang" and position is not PlayerPosition.SELF and index in (1, 2)
                    self._paint_rotated_tile(painter, QPointF(x+offset+index*23, y), 22, 31, tile, rotation, face_down=hidden)
                offset += _MELD_COUNT.get(kind, 3)*23 + 10

    @staticmethod
    def _paint_rotated_tile(painter: QPainter, center: QPointF, width: float, height: float, tile: int | None, rotation: int, *, face_down: bool = False, muted: bool = False, highlight: bool = False) -> None:
        painter.save(); painter.translate(center); painter.rotate(rotation)
        paint_tile(painter, QRectF(-width/2, -height/2, width, height), tile, face_down=face_down, muted=muted, selected=highlight)
        painter.restore()
