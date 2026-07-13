"""PySide6 mouse-first table UI backed exclusively by GameEvent transitions."""

from __future__ import annotations

from functools import partial
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
    QWidget,
)

from ..analysis import analyze_discards, analyze_hand, format_tiles
from ..meld import MeldType
from ..persistence import load_state, save_state
from ..risk.model import BayesianOpponentModel, DiscardRiskPrediction, load_model, predict_discard_risks
from ..risk.observation import observation_from_game_state, observation_to_dict
from ..shanten import calculate_shanten
from ..state import (
    AdvanceTurn, CallExposedGang, CallPeng, DeclareAddedGang,
    DeclareConcealedGang, DeclareWin, DiscardTile, DrawOwnTile, HiddenDraw,
    PlayerPosition, SetOwnInitialHand, StartRound, apply_event, new_game,
    undo_last_event,
)
from ..tiles import TILE_KIND_COUNT, code_to_tile


_POSITION_TEXT = {
    PlayerPosition.SELF: "自己",
    PlayerPosition.LEFT: "上家",
    PlayerPosition.OPPOSITE: "对家",
    PlayerPosition.RIGHT: "下家",
}
_GANG_EVENTS = (CallExposedGang, DeclareConcealedGang, DeclareAddedGang)


class MainWindow(QMainWindow):
    """A compact table recorder that derives every enabled action from state."""

    def __init__(self) -> None:
        super().__init__()
        self.state = new_game()
        self.initial_tiles: list[int] = []
        self.tile_mode = "disabled"
        self.risk_model: BayesianOpponentModel | None = None
        self.risk_predictions: tuple[DiscardRiskPrediction, ...] = ()
        self.setWindowTitle("麻将 AI — 手动记牌桌")
        self.resize(1300, 900)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QGridLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.player_views: dict[PlayerPosition, QTextEdit] = {}
        layout.addWidget(self._player_box(PlayerPosition.OPPOSITE), 0, 1)
        layout.addWidget(self._player_box(PlayerPosition.LEFT), 1, 0)
        layout.addWidget(self._analysis_box(), 1, 1)
        layout.addWidget(self._player_box(PlayerPosition.RIGHT), 1, 2)
        layout.addWidget(self._hand_box(), 2, 0, 1, 3)
        layout.addWidget(self._control_box(), 3, 0, 1, 3)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 1)

    def _player_box(self, position: PlayerPosition) -> QGroupBox:
        box = QGroupBox(_POSITION_TEXT[position])
        inner = QVBoxLayout(box)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setMinimumHeight(130)
        self.player_views[position] = view
        inner.addWidget(view)
        return box

    def _analysis_box(self) -> QGroupBox:
        box = QGroupBox("出牌分析")
        inner = QVBoxLayout(box)
        self.analysis_view = QTextEdit()
        self.analysis_view.setReadOnly(True)
        inner.addWidget(self.analysis_view)
        button = QPushButton("分析自己的手牌")
        button.clicked.connect(self._analyze)
        inner.addWidget(button)
        return box

    def _hand_box(self) -> QGroupBox:
        box = QGroupBox("自己的暗手牌（轮到自己弃牌时，直接点击牌）")
        self.hand_layout = QHBoxLayout(box)
        self.hand_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return box

    def _control_box(self) -> QGroupBox:
        box = QGroupBox("牌局录入")
        outer = QVBoxLayout(box)
        header = QHBoxLayout()
        header.addWidget(QLabel("庄家："))
        self.dealer_combo = QComboBox()
        for position in PlayerPosition:
            self.dealer_combo.addItem(_POSITION_TEXT[position], position)
        header.addWidget(self.dealer_combo)
        for text, callback in (("新一局", self._new_round), ("撤销", self._undo), ("保存", self._save), ("加载", self._load)):
            button = QPushButton(text)
            button.clicked.connect(callback)
            header.addWidget(button)
        risk_load = QPushButton("加载风险模型")
        risk_load.clicked.connect(self._load_risk_model)
        header.addWidget(risk_load)
        risk_export = QPushButton("导出公开状态")
        risk_export.clicked.connect(self._export_observation)
        header.addWidget(risk_export)
        header.addStretch()
        outer.addLayout(header)

        self.context_label = QLabel()
        self.context_label.setWordWrap(True)
        outer.addWidget(self.context_label)
        self.action_layout = QHBoxLayout()
        outer.addLayout(self.action_layout)

        self.tile_grid = QGridLayout()
        self.tile_buttons: list[QPushButton] = []
        for tile in range(TILE_KIND_COUNT):
            button = QPushButton(code_to_tile(tile))
            button.setMinimumWidth(44)
            button.clicked.connect(partial(self._tile_clicked, tile))
            self.tile_grid.addWidget(button, tile // 9, tile % 9)
            self.tile_buttons.append(button)
        outer.addLayout(self.tile_grid)
        self.initial_label = QLabel()
        outer.addWidget(self.initial_label)
        return box

    def _new_round(self) -> None:
        try:
            self.state = apply_event(new_game(), StartRound(self.dealer_combo.currentData()))
            self.initial_tiles = []
            self.analysis_view.clear()
            self._refresh()
        except ValueError as error:
            self._error(error)

    def _tile_clicked(self, tile: int) -> None:
        try:
            if self.tile_mode == "initial":
                self.initial_tiles.append(tile)
                self._refresh()
            elif self.tile_mode == "draw":
                self._apply(DrawOwnTile(tile))
            elif self.tile_mode == "discard":
                self._apply(DiscardTile(self.state.current_player, tile))
            elif self.tile_mode == "concealed_gang":
                self._apply(DeclareConcealedGang(self.state.current_player, tile))
            elif self.tile_mode == "added_gang":
                self._apply(DeclareAddedGang(self.state.current_player, tile))
        except ValueError as error:
            self._error(error)

    def _discard_own_tile(self, tile: int) -> None:
        if self.tile_mode != "discard" or self.state.current_player is not PlayerPosition.SELF:
            return
        try:
            self._apply(DiscardTile(PlayerPosition.SELF, tile))
        except ValueError as error:
            self._error(error)

    def _apply_initial_hand(self) -> None:
        try:
            self._apply(SetOwnInitialHand(tuple(self.initial_tiles)))
            self.initial_tiles = []
        except ValueError as error:
            self._error(error)

    def _apply(self, event: object) -> None:
        self.state = apply_event(self.state, event)
        self._refresh()

    def _undo(self) -> None:
        try:
            self.state = undo_last_event(self.state)
            self._refresh()
        except ValueError as error:
            self._error(error)

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存牌局", "", "麻将牌局 (*.json)")
        if path:
            try:
                save_state(path, self.state)
            except (OSError, ValueError) as error:
                self._error(error)

    def _load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "加载牌局", "", "麻将牌局 (*.json)")
        if path:
            try:
                self.state = load_state(path)
                self.initial_tiles = []
                self._refresh()
            except (OSError, ValueError) as error:
                self._error(error)

    def _load_risk_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "加载风险模型", "models", "风险模型 (*.json)")
        if not path:
            return
        try:
            self.risk_model = load_model(path)
            self._refresh()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.risk_model = None
            QMessageBox.warning(self, "加载失败", f"无法加载风险模型：{error}")

    def _export_observation(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出公开状态", "data/current_observation.json", "公开状态 (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(observation_to_dict(observation_from_game_state(self.state)), handle, ensure_ascii=False, indent=2)
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.warning(self, "导出失败", f"无法导出公开状态：{error}")

    def _refresh(self) -> None:
        self._refresh_player_views()
        self._refresh_context_actions()
        self._refresh_risk_analysis()
        self._refresh_hand()

    def _refresh_risk_analysis(self) -> None:
        """Refresh public-only risk when SELF is in a legal discard state."""
        self.risk_predictions = ()
        if self.risk_model is None:
            return
        try:
            self.risk_predictions = predict_discard_risks(self.risk_model, observation_from_game_state(self.state))
        except (ValueError, TypeError) as error:
            self.analysis_view.setPlainText(f"风险模型无法预测：{error}")
            return
        if not self.risk_predictions:
            self.analysis_view.setPlainText("风险预测：当前不是自己的合法弃牌阶段。")
            return
        text = ["弃牌风险（模型估计；三家综合值为条件独立近似）"]
        for prediction in self.risk_predictions:
            details = "  ".join(
                f"{_POSITION_TEXT[risk.target_player]} {risk.deal_in_probability:.2%}"
                for risk in prediction.opponent_risks
            )
            text.append(f"{code_to_tile(prediction.tile)}：综合 {prediction.combined_deal_in_probability:.2%}；{details}")
        self.analysis_view.setPlainText("\n".join(text))

    def _refresh_player_views(self) -> None:
        for position, view in self.player_views.items():
            player = self.state.players[position]
            discards = " ".join(
                code_to_tile(discard.tile)
                + ("【最后】" if discard is self.state.last_discard and discard.called_by is None else "")
                + ("（已使用）" if discard.called_by else "")
                for discard in player.discards
            ) or "无"
            melds = " ".join(f"{self._meld_name(meld.meld_type)} {code_to_tile(meld.tile)}" for meld in player.melds) or "无"
            view.setPlainText(f"暗手：{player.concealed_tile_count} 张\n弃牌：{discards}\n副露：{melds}")
            style = "background: #e8f1ff; border: 3px solid #2563eb; color: #111827;" if position is self.state.current_player else "background: #ffffff; border: 1px solid #cbd5e1; color: #111827;"
            view.setStyleSheet(style)

    def _refresh_hand(self) -> None:
        while self.hand_layout.count():
            item = self.hand_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        enabled = self.tile_mode == "discard" and self.state.current_player is PlayerPosition.SELF
        for tile, count in enumerate(self.state.own_hand):
            for _ in range(count):
                button = QPushButton(code_to_tile(tile))
                button.setEnabled(enabled)
                prediction = next((item for item in self.risk_predictions if item.tile == tile), None)
                if prediction is not None:
                    risk = prediction.combined_deal_in_probability
                    color = "#16a34a" if risk < 0.03 else "#d97706" if risk < 0.08 else "#dc2626"
                    button.setStyleSheet(f"border: 2px solid {color};")
                    button.setToolTip(f"模型估计综合放炮概率：{risk:.2%}")
                button.clicked.connect(partial(self._discard_own_tile, tile))
                self.hand_layout.addWidget(button)

    def _refresh_context_actions(self) -> None:
        while self.action_layout.count():
            item = self.action_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.tile_mode = "disabled"
        if not self.state.events:
            self.context_label.setText("请先选择庄家，再点击“新一局”。")
            self._set_tile_buttons(False)
            self.initial_label.setText("")
            return
        if not self._has_initial_hand():
            expected = self.state.players[PlayerPosition.SELF].concealed_tile_count
            self.tile_mode = "initial"
            self.context_label.setText(f"请点击下方牌面录入自己的初始手牌（需要 {expected} 张）。")
            self._add_action("确认初始手牌", self._apply_initial_hand, len(self.initial_tiles) == expected)
            self._set_tile_buttons(True)
            self.initial_label.setText("已选：" + " ".join(code_to_tile(tile) for tile in self.initial_tiles))
            return

        self.initial_label.setText("")
        if self.state.round_finished:
            winner = self.state.events[-1].player if isinstance(self.state.events[-1], DeclareWin) else None
            winner_text = _POSITION_TEXT[winner] if winner is not None else "未知玩家"
            self.context_label.setText(f"本局已结束：{winner_text}胡牌。可以保存、撤销或开始新一局。")
            self._set_tile_buttons(False)
            return
        current = self.state.current_player
        if self._awaiting_response():
            source = self.state.last_discard.player
            tile = self.state.last_discard.tile
            self.context_label.setText(f"{_POSITION_TEXT[source]} 打出 {code_to_tile(tile)}。请选择响应，或确认无人响应。")
            for player in PlayerPosition:
                if player is not source:
                    if self._call_is_possible(player, tile, 2):
                        self._add_action(f"{_POSITION_TEXT[player]} 碰", partial(self._try_apply, CallPeng(player, tile, source)))
                    if self._call_is_possible(player, tile, 3):
                        self._add_action(f"{_POSITION_TEXT[player]} 明杠", partial(self._try_apply, CallExposedGang(player, tile, source)))
                    if player is not PlayerPosition.SELF or self._self_can_win_on(tile):
                        self._add_action(f"{_POSITION_TEXT[player]} 胡", partial(self._try_apply, DeclareWin(player)))
            self._add_action("无人响应，下一家", partial(self._try_apply, AdvanceTurn(source)))
            self._set_tile_buttons(False)
            return
        if self._needs_replacement_draw():
            if current is PlayerPosition.SELF:
                self.tile_mode = "draw"
                self.context_label.setText("自己杠后补牌：点击下方牌面录入补牌。")
                self._set_tile_buttons(True)
            else:
                self.context_label.setText(f"{_POSITION_TEXT[current]} 杠后补牌：点击“记录暗摸补牌”。")
                self._add_action("记录暗摸补牌", partial(self._try_apply, HiddenDraw(current)))
                self._set_tile_buttons(False)
            return
        if self.state.players[current].concealed_tile_count % 3 == 2:
            self.tile_mode = "discard"
            self.context_label.setText(f"轮到{_POSITION_TEXT[current]}出牌。" if current is PlayerPosition.SELF else f"轮到{_POSITION_TEXT[current]}出牌：点击下方牌面记录其弃牌。")
            if self._concealed_gang_is_possible(current):
                self._add_action("暗杠", self._set_concealed_gang_mode)
            if self._added_gang_is_possible(current):
                self._add_action("补杠", self._set_added_gang_mode)
            self._add_action("胡牌", partial(self._try_apply, DeclareWin(current)))
            self._set_tile_buttons(current is not PlayerPosition.SELF)
            return
        if current is PlayerPosition.SELF:
            self.tile_mode = "draw"
            self.context_label.setText("轮到自己摸牌：点击下方牌面录入摸到的牌。")
            self._set_tile_buttons(True)
        else:
            self.context_label.setText(f"轮到{_POSITION_TEXT[current]}摸牌：点击“记录暗摸”。")
            self._add_action("记录暗摸", partial(self._try_apply, HiddenDraw(current)))
            self._set_tile_buttons(False)

    def _set_tile_buttons(self, enabled: bool) -> None:
        for tile, button in enumerate(self.tile_buttons):
            button.setEnabled(enabled and self._tile_is_enabled(tile))

    def _tile_is_enabled(self, tile: int) -> bool:
        """Prevent palette clicks that would immediately violate tile limits."""
        if self.tile_mode == "initial":
            return self.initial_tiles.count(tile) < 4
        if self.tile_mode == "draw":
            return self._known_tile_count(tile) < 4
        if self.tile_mode == "discard":
            current = self.state.current_player
            if current is PlayerPosition.SELF:
                return self.state.own_hand[tile] > 0
            return self._known_tile_count(tile) < 4
        if self.tile_mode == "concealed_gang":
            current = self.state.current_player
            if current is PlayerPosition.SELF:
                return self.state.own_hand[tile] >= 4
            return self.state.players[current].concealed_tile_count >= 4 and self._known_tile_count(tile) == 0
        if self.tile_mode == "added_gang":
            current = self.state.current_player
            has_peng = any(meld.meld_type is MeldType.PENG and meld.tile == tile for meld in self.state.players[current].melds)
            if current is PlayerPosition.SELF:
                return has_peng and self.state.own_hand[tile] >= 1
            return has_peng and self.state.players[current].concealed_tile_count >= 1 and self._known_tile_count(tile) < 4
        return False

    def _add_action(self, text: str, callback: object, enabled: bool = True) -> None:
        button = QPushButton(text)
        button.setEnabled(enabled)
        button.clicked.connect(callback)
        self.action_layout.addWidget(button)

    def _awaiting_response(self) -> bool:
        discard = self.state.last_discard
        return discard is not None and discard.called_by is None and self.state.current_player is discard.player

    def _call_is_possible(self, player: PlayerPosition, tile: int, required: int) -> bool:
        if self.state.players[player].concealed_tile_count < required:
            return False
        if player is PlayerPosition.SELF and self.state.own_hand[tile] < required:
            return False
        return self._known_tile_count(tile) + required <= 4

    def _concealed_gang_is_possible(self, player: PlayerPosition) -> bool:
        if player is PlayerPosition.SELF:
            return any(count >= 4 for count in self.state.own_hand)
        return self.state.players[player].concealed_tile_count >= 4

    def _added_gang_is_possible(self, player: PlayerPosition) -> bool:
        peng_tiles = [meld.tile for meld in self.state.players[player].melds if meld.meld_type is MeldType.PENG]
        if not peng_tiles or self.state.players[player].concealed_tile_count < 1:
            return False
        if player is PlayerPosition.SELF:
            return any(self.state.own_hand[tile] >= 1 for tile in peng_tiles)
        return any(self._known_tile_count(tile) < 4 for tile in peng_tiles)

    def _known_tile_count(self, tile: int) -> int:
        concealed_gang_tiles = sum(
            meld.tile_count
            for player in self.state.players.values()
            for meld in player.melds
            if meld.meld_type is MeldType.CONCEALED_GANG and meld.tile == tile
        )
        return self.state.own_hand[tile] + self.state.visible_counts[tile] + concealed_gang_tiles

    def _self_can_win_on(self, tile: int) -> bool:
        """Whether the available last discard completes SELF's regular hand."""
        if self.state.own_hand[tile] >= 4:
            return False
        hand = self.state.own_hand.copy()
        hand[tile] += 1
        fixed_melds = len(self.state.players[PlayerPosition.SELF].melds)
        return calculate_shanten(hand, fixed_melds=fixed_melds) == -1

    def _needs_replacement_draw(self) -> bool:
        return bool(self.state.events) and isinstance(self.state.events[-1], _GANG_EVENTS)

    def _set_concealed_gang_mode(self) -> None:
        self.tile_mode = "concealed_gang"
        self.context_label.setText(f"请选择{_POSITION_TEXT[self.state.current_player]}要暗杠的牌。")
        self._set_tile_buttons(True)
        self._refresh_hand()

    def _set_added_gang_mode(self) -> None:
        self.tile_mode = "added_gang"
        self.context_label.setText(f"请选择{_POSITION_TEXT[self.state.current_player]}要补杠的牌。")
        self._set_tile_buttons(True)
        self._refresh_hand()

    def _try_apply(self, event: object) -> None:
        try:
            self._apply(event)
        except ValueError as error:
            self._error(error)

    def _has_initial_hand(self) -> bool:
        return any(isinstance(event, SetOwnInitialHand) for event in self.state.events)

    def _analyze(self) -> None:
        try:
            if self.state.current_player is not PlayerPosition.SELF:
                raise ValueError("只有轮到自己时才能分析手牌")
            own_melds = self.state.players[PlayerPosition.SELF].melds
            unavailable = self.state.visible_counts.copy()
            for meld in own_melds:
                if meld.meld_type is MeldType.CONCEALED_GANG:
                    unavailable[meld.tile] += meld.tile_count
            result = analyze_hand(self.state.own_hand, unavailable, fixed_melds=len(own_melds))
            text = [f"向听数：{result.shanten}", f"听牌：{format_tiles(result.winning_tiles)}", f"有效牌：{format_tiles(result.effective_tiles)}"]
            if result.effective_tiles:
                text.append("有效牌剩余：" + "，".join(f"{code_to_tile(tile)}={result.remaining_by_tile[tile]}" for tile in result.effective_tiles))
            if sum(self.state.own_hand) % 3 == 2:
                candidates = analyze_discards(self.state.own_hand, unavailable, fixed_melds=len(own_melds))
                if candidates:
                    text.append(f"推荐弃牌：{code_to_tile(candidates[0].discard)}")
                    text.append("候选弃牌：")
                    text.extend(f"{code_to_tile(item.discard)}：向听 {item.analysis.shanten}，受入 {item.analysis.total_effective_tiles}" for item in candidates)
            self.analysis_view.setPlainText("\n".join(text))
        except ValueError as error:
            self._error(error)

    @staticmethod
    def _meld_name(meld_type: MeldType) -> str:
        return {MeldType.PENG: "碰", MeldType.EXPOSED_GANG: "明杠", MeldType.CONCEALED_GANG: "暗杠", MeldType.ADDED_GANG: "补杠"}[meld_type]

    def _error(self, error: Exception) -> None:
        QMessageBox.warning(self, "操作无效", f"该操作不符合当前牌局状态。\n\n原因：{self._error_reason(error)}")

    @staticmethod
    def _error_reason(error: Exception) -> str:
        text = str(error)
        translations = {
            "the round has already finished": "本局已经结束。",
            "only the current player may win without an available last discard": "这不是可胡的最后一张弃牌。",
            "the last discard is no longer available for calls": "该弃牌已经过了响应时机。",
            "a tile kind exceeds the configured copy limit": "该牌加上已知牌会超过四张。",
        }
        return translations.get(text, "请检查当前轮次、手牌数量、最后一张弃牌或副露条件。")


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
