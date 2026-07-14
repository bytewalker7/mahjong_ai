"""Tabletop desktop UI for one human player versus three local AI players."""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import QEvent, QPropertyAnimation, QTimer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGraphicsOpacityEffect, QMainWindow, QMessageBox,
    QPushButton, QToolBar,
)

from ..game.session import GameSession
from ..simulator.models import (
    AddedGangAction, ConcealedGangAction, DiscardAction, ExposedGangAction,
    PassAction, PengAction, RonAction, TsumoAction,
)
from ..tiles import code_to_tile
from .widgets.action_button import RoundActionButton
from .widgets.table_widget import MahjongTableWidget


class GameWindow(QMainWindow):
    """Visual layer; every real action still travels through GameSession."""

    def __init__(self) -> None:
        super().__init__()
        self.session = GameSession()
        self.selected_tile: int | None = None
        self._show_gang_choices = False
        self._action_buttons: list[RoundActionButton] = []
        self.timer = QTimer(self); self.timer.timeout.connect(self._advance_automatic)
        self.setWindowTitle("麻将 AI — 单机四人麻将桌")
        self.resize(1280, 820); self.setMinimumSize(980, 680)
        self.table = MahjongTableWidget(self); self.table.tile_clicked.connect(self._hand_tile_clicked); self.table.empty_clicked.connect(self._clear_selection)
        self.table.installEventFilter(self); self.setCentralWidget(self.table)
        self._build_toolbar(); self.statusBar().showMessage("正在开始新游戏……")
        self._refresh(); self._schedule_automatic()

    def _build_toolbar(self) -> None:
        bar = QToolBar("游戏"); bar.setMovable(False); self.addToolBar(bar)
        new_game = QPushButton("新游戏"); new_game.clicked.connect(self._new_game); bar.addWidget(new_game)
        bar.addSeparator()
        exit_button = QPushButton("退出游戏"); exit_button.clicked.connect(self.close); bar.addWidget(exit_button)
        bar.addSeparator()
        speed_label = QPushButton("AI 速度："); speed_label.setEnabled(False); bar.addWidget(speed_label)
        self.speed = QComboBox(); self.speed.addItem("快 0.25 秒", 250); self.speed.addItem("正常 0.55 秒", 550); self.speed.addItem("慢 0.9 秒", 900); self.speed.setCurrentIndex(1); bar.addWidget(self.speed)

    def eventFilter(self, watched, event):
        if watched is self.table and event.type() is QEvent.Type.Resize:
            self._layout_actions()
        return super().eventFilter(watched, event)

    def _new_game(self) -> None:
        self.timer.stop(); self.selected_tile = None; self._show_gang_choices = False
        self.session.new_game(); self._refresh(); self._schedule_automatic()

    def _schedule_automatic(self) -> None:
        if self.session.advance_automatic_step():
            self._refresh(); self.timer.start(int(self.speed.currentData()))
        else:
            self.timer.stop()

    def _advance_automatic(self) -> None:
        if self.session.advance_automatic_step():
            self._refresh()
        else:
            self.timer.stop(); self._refresh()

    def _hand_tile_clicked(self, tile: int) -> None:
        legal_tiles = {action.tile for action in self.session.human_legal_actions() if isinstance(action, DiscardAction)}
        if tile not in legal_tiles:
            return
        if self.selected_tile == tile:
            self._apply_human(DiscardAction(tile))
        else:
            self.selected_tile = tile
            self.table.set_game(self.session.view(), self.session.human_legal_actions(), self.selected_tile)
            self.statusBar().showMessage(f"已选择 {code_to_tile(tile)}；再次点击同一张牌确认弃牌")

    def _clear_selection(self) -> None:
        if self.selected_tile is not None:
            self.selected_tile = None; self.table.set_game(self.session.view(), self.session.human_legal_actions(), None)

    def _apply_human(self, action) -> None:
        try:
            self.selected_tile = None; self._show_gang_choices = False
            self.session.apply_human_action(action)
            self._refresh(); self._schedule_automatic()
        except ValueError as error:
            QMessageBox.warning(self, "操作无效", str(error))

    def _refresh(self) -> None:
        view = self.session.view(); legal = self.session.human_legal_actions()
        if not any(isinstance(action, DiscardAction) and action.tile == self.selected_tile for action in legal):
            self.selected_tile = None
        self.table.set_game(view, legal, self.selected_tile)
        self._refresh_actions(legal)
        if view.finished:
            winner = "无人" if view.winner is None else {0: "自己", 1: "上家 AI", 2: "对家 AI", 3: "下家 AI"}[int(view.winner)]
            method = {"ron": "点炮胡", "tsumo": "自摸", "draw": "流局"}.get(view.result, str(view.result))
            scores = "  ".join(f"{position.name} {value:+d}" for position, value in (view.final_scores or {}).items())
            self.statusBar().showMessage(f"本局结束：{winner} {method}。{scores}")
        elif legal:
            self.statusBar().showMessage("轮到你：选择牌后再次点击确认弃牌，或使用右侧圆形操作按钮。")
        else:
            self.statusBar().showMessage("AI 正在行动……")

    def _refresh_actions(self, legal) -> None:
        for button in self._action_buttons:
            button.deleteLater()
        self._action_buttons = []
        if not legal:
            return
        specials = [action for action in legal if not isinstance(action, DiscardAction)]
        gang_actions = [action for action in specials if isinstance(action, (ExposedGangAction, ConcealedGangAction, AddedGangAction))]
        if self._show_gang_choices and gang_actions:
            for action in gang_actions:
                label = f"杠\n{code_to_tile(action.tile)}" if hasattr(action, "tile") else "杠"
                self._add_action_button(label, action)
            self._add_action_button("过", PassAction()) if any(isinstance(action, PassAction) for action in specials) else None
        else:
            for action in specials:
                if isinstance(action, (ConcealedGangAction, AddedGangAction, ExposedGangAction)):
                    continue
                if isinstance(action, (TsumoAction, RonAction)): self._add_action_button("胡", action)
                elif isinstance(action, PengAction): self._add_action_button("碰", action)
                elif isinstance(action, PassAction): self._add_action_button("过", action)
            if gang_actions:
                self._add_action_button("杠", None)
        self._layout_actions()

    def _add_action_button(self, label: str, action) -> None:
        button = RoundActionButton(label, self.table); button.setFixedSize(72, 72)
        if action is None:
            button.clicked.connect(self._open_gang_choices)
        else:
            button.clicked.connect(partial(self._apply_human, action))
        effect = QGraphicsOpacityEffect(button); button.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", button); animation.setDuration(180); animation.setStartValue(0.0); animation.setEndValue(1.0); animation.start(); button._fade_animation = animation
        button.show(); self._action_buttons.append(button)

    def _open_gang_choices(self) -> None:
        self._show_gang_choices = True; self._refresh_actions(self.session.human_legal_actions())

    def _layout_actions(self) -> None:
        if not self._action_buttons:
            return
        gap, size = 10, 72
        total = len(self._action_buttons) * size + (len(self._action_buttons) - 1) * gap
        x = self.table.width() - total - 40; y = self.table.height() - 205
        for button in self._action_buttons:
            button.move(x, y); x += size + gap


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = GameWindow(); window.show(); app.exec()
