"""PySide6 desktop table for entering public Mahjong events by mouse."""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
    QWidget,
)

from ..analysis import analyze_discards, analyze_hand, format_tiles
from ..meld import MeldType
from ..persistence import load_state, save_state
from ..state import (
    AdvanceTurn, CallExposedGang, CallPeng, DeclareAddedGang,
    DeclareConcealedGang, DeclareWin, DiscardTile, DrawOwnTile, GameState,
    HiddenDraw, PlayerPosition, SetOwnInitialHand, StartRound, apply_event,
    new_game, undo_last_event,
)
from ..tiles import TILE_KIND_COUNT, code_to_tile


class MainWindow(QMainWindow):
    """A mouse-first adapter that only changes state through game events."""

    def __init__(self) -> None:
        super().__init__()
        self.state = new_game()
        self.selected_player = PlayerPosition.SELF
        self.initial_tiles: list[int] = []
        self.setWindowTitle("mahjong_ai — Manual Table Recorder")
        self.resize(1250, 860)
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
        layout.addWidget(self._controls_box(), 3, 0, 1, 3)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 1)

    def _player_box(self, position: PlayerPosition) -> QGroupBox:
        box = QGroupBox(position.name)
        inner = QVBoxLayout(box)
        choose = QPushButton(f"Select {position.name}")
        choose.clicked.connect(partial(self._select_player, position))
        inner.addWidget(choose)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setMinimumHeight(120)
        self.player_views[position] = view
        inner.addWidget(view)
        return box

    def _analysis_box(self) -> QGroupBox:
        box = QGroupBox("Analysis")
        inner = QVBoxLayout(box)
        self.analysis_view = QTextEdit()
        self.analysis_view.setReadOnly(True)
        inner.addWidget(self.analysis_view)
        analyze = QPushButton("Analyze SELF")
        analyze.clicked.connect(self._analyze)
        inner.addWidget(analyze)
        return box

    def _hand_box(self) -> QGroupBox:
        box = QGroupBox("SELF concealed hand — click a tile to discard when it is SELF's turn")
        self.hand_layout = QHBoxLayout(box)
        self.hand_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return box

    def _controls_box(self) -> QGroupBox:
        box = QGroupBox("Event controls")
        outer = QVBoxLayout(box)
        row = QHBoxLayout()
        self.player_combo = QComboBox()
        self.from_combo = QComboBox()
        for position in PlayerPosition:
            self.player_combo.addItem(position.name, position)
            self.from_combo.addItem(position.name, position)
        self.action_combo = QComboBox()
        self.action_combo.addItems(["draw", "discard", "peng", "exposed_gang", "concealed_gang", "added_gang"])
        row.addWidget(QLabel("Player")); row.addWidget(self.player_combo)
        row.addWidget(QLabel("Action")); row.addWidget(self.action_combo)
        row.addWidget(QLabel("From")); row.addWidget(self.from_combo)
        outer.addLayout(row)

        palette = QGridLayout()
        for tile in range(TILE_KIND_COUNT):
            button = QPushButton(code_to_tile(tile))
            button.setMinimumWidth(42)
            button.clicked.connect(partial(self._tile_action, tile))
            palette.addWidget(button, tile // 9, tile % 9)
        outer.addLayout(palette)

        actions = QHBoxLayout()
        for label, callback in (
            ("New round", self._new_round),
            ("Apply initial hand", self._apply_initial_hand),
            ("Hidden draw", self._hidden_draw),
            ("Next player", self._next_player),
            ("Win", self._win),
            ("Undo", self._undo),
            ("Save", self._save),
            ("Load", self._load),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        outer.addLayout(actions)
        self.initial_label = QLabel("Initial hand: click tiles while no initial hand has been applied.")
        outer.addWidget(self.initial_label)
        return box

    def _select_player(self, player: PlayerPosition) -> None:
        self.selected_player = player
        self.player_combo.setCurrentIndex(self.player_combo.findData(player))
        self._refresh()

    def _chosen_player(self) -> PlayerPosition:
        return self.player_combo.currentData()

    def _chosen_from(self) -> PlayerPosition:
        return self.from_combo.currentData()

    def _tile_action(self, tile: int) -> None:
        if not self._has_initial_hand():
            self.initial_tiles.append(tile)
            self._refresh()
            return
        player = self._chosen_player()
        action = self.action_combo.currentText()
        try:
            if action == "draw":
                if player is not PlayerPosition.SELF:
                    raise ValueError("only SELF draws a known tile; use Hidden draw for other players")
                self._apply(DrawOwnTile(tile))
            elif action == "discard":
                self._apply(DiscardTile(player, tile))
            elif action == "peng":
                self._apply(CallPeng(player, tile, self._chosen_from()))
            elif action == "exposed_gang":
                self._apply(CallExposedGang(player, tile, self._chosen_from()))
            elif action == "concealed_gang":
                self._apply(DeclareConcealedGang(player, tile))
            elif action == "added_gang":
                self._apply(DeclareAddedGang(player, tile))
        except ValueError as error:
            self._error(error)

    def _discard_hand_tile(self, tile: int) -> None:
        try:
            self._apply(DiscardTile(PlayerPosition.SELF, tile))
        except ValueError as error:
            self._error(error)

    def _new_round(self) -> None:
        self.state = apply_event(new_game(), StartRound(self._chosen_player()))
        self.initial_tiles = []
        self.analysis_view.clear()
        self._refresh()

    def _apply_initial_hand(self) -> None:
        try:
            self._apply(SetOwnInitialHand(tuple(self.initial_tiles)))
            self.initial_tiles = []
        except ValueError as error:
            self._error(error)

    def _hidden_draw(self) -> None:
        try:
            self._apply(HiddenDraw(self._chosen_player()))
        except ValueError as error:
            self._error(error)

    def _next_player(self) -> None:
        try:
            self._apply(AdvanceTurn(self.state.current_player))
        except ValueError as error:
            self._error(error)

    def _win(self) -> None:
        try:
            self._apply(DeclareWin(self._chosen_player()))
        except ValueError as error:
            self._error(error)

    def _undo(self) -> None:
        try:
            self.state = undo_last_event(self.state)
            self._refresh()
        except ValueError as error:
            self._error(error)

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save round", "", "Mahjong JSON (*.json)")
        if path:
            try:
                save_state(path, self.state)
            except (OSError, ValueError) as error:
                self._error(error)

    def _load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load round", "", "Mahjong JSON (*.json)")
        if path:
            try:
                self.state = load_state(path)
                self.initial_tiles = []
                self._refresh()
            except (OSError, ValueError) as error:
                self._error(error)

    def _apply(self, event: object) -> None:
        self.state = apply_event(self.state, event)
        self._refresh()

    def _has_initial_hand(self) -> bool:
        return any(type(event).__name__ == "SetOwnInitialHand" for event in self.state.events)

    def _refresh(self) -> None:
        for position, view in self.player_views.items():
            player = self.state.players[position]
            discards = " ".join(
                code_to_tile(item.tile)
                + (" [LAST]" if item is self.state.last_discard and item.called_by is None else "")
                + ("*" if item.called_by else "")
                for item in player.discards
            ) or "—"
            melds = " ".join(f"{item.meld_type.value}:{code_to_tile(item.tile)}" for item in player.melds) or "—"
            view.setPlainText(f"Concealed: {player.concealed_tile_count}\nDiscards: {discards}\nMelds: {melds}")
            view.setStyleSheet("background: #fff2a8;" if position is self.state.current_player else "")
        while self.hand_layout.count():
            item = self.hand_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for tile, count in enumerate(self.state.own_hand):
            for _ in range(count):
                button = QPushButton(code_to_tile(tile))
                button.clicked.connect(partial(self._discard_hand_tile, tile))
                self.hand_layout.addWidget(button)
        self.initial_label.setText("Initial hand selection: " + " ".join(code_to_tile(tile) for tile in self.initial_tiles))

    def _analyze(self) -> None:
        try:
            if self.state.current_player is not PlayerPosition.SELF:
                raise ValueError("analysis is available only when it is SELF's turn")
            own_melds = self.state.players[PlayerPosition.SELF].melds
            unavailable = self.state.visible_counts.copy()
            for meld in own_melds:
                if meld.meld_type is MeldType.CONCEALED_GANG:
                    unavailable[meld.tile] += meld.tile_count
            result = analyze_hand(self.state.own_hand, unavailable, fixed_melds=len(own_melds))
            text = [f"Shanten: {result.shanten}", f"Waits: {format_tiles(result.winning_tiles)}", f"Effective: {format_tiles(result.effective_tiles)}"]
            if sum(self.state.own_hand) % 3 == 2:
                candidates = analyze_discards(self.state.own_hand, unavailable, fixed_melds=len(own_melds))
                if candidates:
                    text.append(f"Recommended discard: {code_to_tile(candidates[0].discard)}")
                    text.extend(f"{code_to_tile(item.discard)}: shanten {item.analysis.shanten}, remaining {item.analysis.total_effective_tiles}" for item in candidates)
            self.analysis_view.setPlainText("\n".join(text))
        except ValueError as error:
            self._error(error)

    def _error(self, error: Exception) -> None:
        QMessageBox.warning(self, "Invalid operation", str(error))


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
