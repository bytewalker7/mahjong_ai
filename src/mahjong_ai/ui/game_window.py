"""Desktop UI for one human player against three local AI players."""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from ..game.session import GameSession, PublicGameView
from ..meld import MeldType
from ..simulator.models import (
    AddedGangAction, ConcealedGangAction, DiscardAction, ExposedGangAction,
    PassAction, PengAction, RonAction, TsumoAction,
)
from ..state.models import PlayerPosition
from ..tiles import code_to_tile


_NAMES = {
    PlayerPosition.SELF: "自己", PlayerPosition.LEFT: "上家 AI",
    PlayerPosition.OPPOSITE: "对家 AI", PlayerPosition.RIGHT: "下家 AI",
}
_MELD_NAMES = {
    "peng": "碰", "exposed_gang": "明杠", "concealed_gang": "暗杠", "added_gang": "补杠",
}


class GameWindow(QMainWindow):
    """Rendering is based solely on ``PublicGameView.observation``."""

    def __init__(self) -> None:
        super().__init__()
        self.session = GameSession()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_automatic)
        self.setWindowTitle("麻将 AI — 单机四人麻将")
        self.resize(1380, 920)
        self._build_ui()
        self._refresh()
        self._schedule_automatic()

    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        layout = QGridLayout(root); layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(10)
        self.player_views: dict[PlayerPosition, QTextEdit] = {}
        layout.addWidget(self._player_box(PlayerPosition.OPPOSITE), 0, 1)
        layout.addWidget(self._player_box(PlayerPosition.LEFT), 1, 0)
        layout.addWidget(self._center_box(), 1, 1)
        layout.addWidget(self._player_box(PlayerPosition.RIGHT), 1, 2)
        layout.addWidget(self._hand_box(), 2, 0, 1, 3)
        layout.addWidget(self._control_box(), 3, 0, 1, 3)
        layout.setColumnStretch(0, 1); layout.setColumnStretch(1, 2); layout.setColumnStretch(2, 1)

    def _player_box(self, position: PlayerPosition) -> QGroupBox:
        box = QGroupBox(_NAMES[position]); inner = QVBoxLayout(box)
        view = QTextEdit(); view.setReadOnly(True); view.setMinimumHeight(145)
        self.player_views[position] = view; inner.addWidget(view)
        return box

    def _center_box(self) -> QGroupBox:
        box = QGroupBox("牌桌信息"); inner = QVBoxLayout(box)
        self.status_label = QLabel(); self.status_label.setWordWrap(True); inner.addWidget(self.status_label)
        self.result_view = QTextEdit(); self.result_view.setReadOnly(True); inner.addWidget(self.result_view)
        return box

    def _hand_box(self) -> QGroupBox:
        box = QGroupBox("自己的手牌（轮到自己弃牌时，直接点击牌面）")
        self.hand_layout = QHBoxLayout(box); self.hand_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return box

    def _control_box(self) -> QGroupBox:
        box = QGroupBox("游戏操作"); outer = QVBoxLayout(box)
        header = QHBoxLayout()
        new_game = QPushButton("新游戏"); new_game.clicked.connect(self._new_game); header.addWidget(new_game)
        exit_button = QPushButton("退出游戏"); exit_button.clicked.connect(self.close); header.addWidget(exit_button)
        header.addWidget(QLabel("AI 行动速度："))
        self.speed = QComboBox()
        self.speed.addItem("快（0.2 秒）", 200); self.speed.addItem("正常（0.6 秒）", 600); self.speed.addItem("慢（1.0 秒）", 1000)
        self.speed.setCurrentIndex(1); header.addWidget(self.speed); header.addStretch(); outer.addLayout(header)
        self.action_label = QLabel(); self.action_label.setWordWrap(True); outer.addWidget(self.action_label)
        self.action_layout = QHBoxLayout(); outer.addLayout(self.action_layout)
        return box

    def _new_game(self) -> None:
        self.timer.stop(); self.session.new_game(); self._refresh(); self._schedule_automatic()

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

    def _apply_human(self, action) -> None:
        try:
            self.session.apply_human_action(action)
            self._refresh(); self._schedule_automatic()
        except ValueError as error:
            QMessageBox.warning(self, "操作无效", str(error))

    def _refresh(self) -> None:
        view = self.session.view(); observation = view.observation
        self._refresh_players(view)
        self._refresh_hand(view)
        self._refresh_actions(view)
        if view.finished:
            winner = _NAMES[view.winner] if view.winner is not None else "无人"
            result_name = {"ron": "点炮胡", "tsumo": "自摸", "draw": "流局"}.get(view.result, str(view.result))
            scores = "\n".join(f"{_NAMES[position]}：{view.final_scores[position]:+d} 分" for position in PlayerPosition) if view.final_scores else ""
            self.status_label.setText(f"本局结束：{winner}，{result_name}")
            self.result_view.setPlainText(scores)
        else:
            self.status_label.setText(f"剩余牌：{observation.wall_remaining} 张    当前行动：{_NAMES[observation.current_player]}")
            self.result_view.setPlainText("")

    def _refresh_players(self, view: PublicGameView) -> None:
        observation = view.observation
        for index, position in enumerate(PlayerPosition):
            if position is PlayerPosition.SELF:
                continue
            discards = " ".join(code_to_tile(tile) + ("（已用）" if used else "") for tile, used in observation.public_discards[index]) or "无"
            melds = " ".join(f"{_MELD_NAMES[kind]} {code_to_tile(tile) if tile is not None else '牌背'}" for kind, tile in observation.public_melds[index]) or "无"
            hand_info = f"手牌：{' '.join(code_to_tile(tile) for tile, count in enumerate(observation.own_hand) for _ in range(count))}" if position is PlayerPosition.SELF else f"暗手：牌背 × {observation.concealed_tile_counts[index]}"
            self.player_views[position].setPlainText(f"{hand_info}\n弃牌：{discards}\n副露：{melds}")
            active = position is observation.current_player and not view.finished
            self.player_views[position].setStyleSheet("border: 3px solid #2563eb; background: #eef5ff; color: #111827;" if active else "border: 1px solid #cbd5e1; background: #ffffff; color: #111827;")

    def _refresh_hand(self, view: PublicGameView) -> None:
        while self.hand_layout.count():
            item = self.hand_layout.takeAt(0)
            if item.widget() is not None: item.widget().deleteLater()
        legal = self.session.human_legal_actions()
        discard_tiles = {action.tile for action in legal if isinstance(action, DiscardAction)}
        for tile, count in enumerate(view.observation.own_hand):
            for _ in range(count):
                button = QPushButton(code_to_tile(tile)); button.setEnabled(tile in discard_tiles)
                button.clicked.connect(partial(self._apply_human, DiscardAction(tile)))
                self.hand_layout.addWidget(button)

    def _refresh_actions(self, view: PublicGameView) -> None:
        while self.action_layout.count():
            item = self.action_layout.takeAt(0)
            if item.widget() is not None: item.widget().deleteLater()
        legal = self.session.human_legal_actions()
        if view.finished:
            self.action_label.setText("点击“新游戏”开始下一局。"); return
        if not legal:
            self.action_label.setText("等待 AI 行动……"); return
        self.action_label.setText("请选择当前合法操作：")
        for action in legal:
            if isinstance(action, DiscardAction): continue
            if isinstance(action, TsumoAction): text = "胡（自摸）"
            elif isinstance(action, RonAction): text = "胡（点炮）"
            elif isinstance(action, PengAction): text = "碰"
            elif isinstance(action, ExposedGangAction): text = "明杠"
            elif isinstance(action, ConcealedGangAction): text = f"暗杠 {code_to_tile(action.tile)}"
            elif isinstance(action, AddedGangAction): text = f"补杠 {code_to_tile(action.tile)}"
            elif isinstance(action, PassAction): text = "放弃"
            else: continue
            button = QPushButton(text); button.clicked.connect(partial(self._apply_human, action)); self.action_layout.addWidget(button)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = GameWindow(); window.show(); app.exec()
