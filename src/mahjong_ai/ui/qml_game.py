"""Qt Quick game launcher and public-state bridge.

QML sees only values derived from :class:`PublicGameView`.  All state changes
are submitted through :class:`GameSession`, which in turn uses
``MahjongEnvironment.step`` and its legal action list.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # PySide6-Essentials can run the game without optional audio.
    QAudioOutput = QMediaPlayer = None  # type: ignore[assignment,misc]

from ..game.session import GameSession
from ..simulator.models import (
    Action,
    AddedGangAction,
    ConcealedGangAction,
    DiscardAction,
    ExposedGangAction,
    PassAction,
    PengAction,
    Phase,
    RonAction,
    TsumoAction,
)
from ..state.models import PlayerPosition
from ..tiles import code_to_tile


_MELD_SIZE = {"peng": 3, "exposed_gang": 4, "concealed_gang": 4, "added_gang": 4}


def _find_background_music(music_directory: Path) -> Path | None:
    """Prefer lossless WAV while retaining the original MP3 fallback."""
    return next(
        (
            music_directory / filename
            for filename in ("background music.wav", "background music.mp3")
            if (music_directory / filename).exists()
        ),
        None,
    )


class GameBridge(QObject):
    """Expose immutable public snapshots and legal UI commands to QML."""

    stateChanged = Signal()
    musicChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, *, seed: int | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session = GameSession(seed=seed)
        self._selected_index: int | None = None
        self._action_map: dict[str, Action] = {}
        self._ai_delay_ms = 550
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._advance_automatic)
        self._music_player = None
        self._audio_output = None
        self._music_enabled = True
        self._setup_background_music()
        self._rebuild_action_map()

    def _setup_background_music(self) -> None:
        if QMediaPlayer is None or QAudioOutput is None:
            return
        music_directory = Path(__file__).parents[1] / "assets" / "music"
        music_path = _find_background_music(music_directory)
        if music_path is None:
            return
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.32)
        self._music_player = QMediaPlayer(self)
        self._music_player.setAudioOutput(self._audio_output)
        self._music_player.setSource(QUrl.fromLocalFile(str(music_path)))
        self._music_player.setLoops(QMediaPlayer.Loops.Infinite)

    @property
    def session(self) -> GameSession:
        """Test hook; never registered as a QML context property."""
        return self._session

    def _view(self):
        return self._session.view()

    def _observation(self):
        return self._view().observation

    def _legal(self) -> tuple[Action, ...]:
        return self._session.human_legal_actions()

    def _emit_state(self) -> None:
        legal_discards = {action.tile for action in self._legal() if isinstance(action, DiscardAction)}
        ordered_hand = self._ordered_hand()
        if (
            self._selected_index is None
            or self._selected_index >= len(ordered_hand)
            or ordered_hand[self._selected_index] not in legal_discards
        ):
            self._selected_index = None
        self._rebuild_action_map()
        self.stateChanged.emit()

    def _rebuild_action_map(self) -> None:
        self._action_map.clear()
        specials = [action for action in self._legal() if not isinstance(action, DiscardAction)]
        priority = lambda action: (
            0 if isinstance(action, (RonAction, TsumoAction)) else
            1 if isinstance(action, PengAction) else
            2 if isinstance(action, (ExposedGangAction, ConcealedGangAction, AddedGangAction)) else
            3
        )
        specials.sort(key=priority)
        for index, action in enumerate(specials):
            self._action_map[f"action_{index}"] = action

    def _schedule_automatic(self) -> None:
        view = self._view()
        if view.finished:
            self._timer.stop()
            return
        observation = view.observation
        legal = self._legal()
        forced_human_draw = observation.current_player is PlayerPosition.SELF and observation.phase in {
            Phase.DRAW,
            Phase.REPLACEMENT_DRAW,
        }
        automatic_human_pass = len(legal) == 1 and isinstance(legal[0], PassAction)
        if observation.current_player is not PlayerPosition.SELF or forced_human_draw or automatic_human_pass:
            self._timer.start(0 if automatic_human_pass else self._ai_delay_ms)
        else:
            self._timer.stop()

    @Slot()
    def start(self) -> None:
        if self._music_enabled and self._music_player is not None:
            self._music_player.play()
        self._emit_state()
        self._schedule_automatic()

    @Slot()
    def newGame(self) -> None:
        self._timer.stop()
        self._selected_index = None
        self._session.new_game()
        self._emit_state()
        self._schedule_automatic()

    @Slot(int)
    def setAiDelay(self, milliseconds: int) -> None:
        self._ai_delay_ms = max(100, min(2000, int(milliseconds)))

    @Slot()
    def toggleMusic(self) -> None:
        if self._music_player is None:
            self.errorOccurred.emit("音乐播放器不可用，请安装 PySide6-Addons")
            return
        self._music_enabled = not self._music_enabled
        if self._music_enabled:
            self._music_player.play()
        else:
            self._music_player.pause()
        self.musicChanged.emit()

    @Slot(int)
    def clickTileAt(self, index: int) -> None:
        tiles = self._ordered_hand()
        if not 0 <= index < len(tiles):
            return
        tile = tiles[index]
        legal_tiles = {action.tile for action in self._legal() if isinstance(action, DiscardAction)}
        if tile not in legal_tiles:
            return
        if self._selected_index != index:
            self._selected_index = index
            self.stateChanged.emit()
            return
        self._selected_index = None
        self._apply_action(DiscardAction(tile))

    @Slot(int)
    def clickTile(self, tile: int) -> None:
        """Compatibility slot: select the first matching physical tile."""
        try:
            index = self._ordered_hand().index(tile)
        except ValueError:
            return
        self.clickTileAt(index)

    @Slot()
    def clearSelection(self) -> None:
        if self._selected_index is not None:
            self._selected_index = None
            self.stateChanged.emit()

    @Slot(str)
    def performAction(self, key: str) -> None:
        action = self._action_map.get(key)
        if action is not None:
            self._apply_action(action)

    def _apply_action(self, action: Action) -> None:
        try:
            self._session.apply_human_action(action)
        except ValueError as error:
            self.errorOccurred.emit(str(error))
            return
        self._selected_index = None
        self._emit_state()
        self._schedule_automatic()

    @Slot()
    def _advance_automatic(self) -> None:
        try:
            legal = self._legal()
            if len(legal) == 1 and isinstance(legal[0], PassAction):
                self._session.apply_human_action(legal[0])
                advanced = True
            else:
                advanced = self._session.advance_automatic_step()
        except ValueError as error:
            self.errorOccurred.emit(str(error))
            return
        if advanced:
            self._emit_state()
        self._schedule_automatic()

    @Slot()
    def quit(self) -> None:
        app = QGuiApplication.instance()
        if app is not None:
            app.quit()

    def _ordered_hand(self) -> list[int]:
        view = self._view()
        tiles = [tile for tile, count in enumerate(view.observation.own_hand) for _ in range(count)]
        if view.drawn_tile is not None and view.drawn_tile in tiles:
            tiles.remove(view.drawn_tile)
            tiles.append(view.drawn_tile)
        return tiles

    def _hand_tiles(self) -> list[dict[str, object]]:
        view = self._view()
        tiles = self._ordered_hand()
        legal = {action.tile for action in self._legal() if isinstance(action, DiscardAction)}
        return [
            {
                "instance": index,
                "tile": tile,
                "code": code_to_tile(tile),
                "legal": tile in legal,
                "selected": index == self._selected_index,
                "drawn": view.drawn_tile is not None and index == len(tiles) - 1,
            }
            for index, tile in enumerate(tiles)
        ]

    def _discard_codes(self, position: PlayerPosition) -> list[dict[str, object]]:
        view = self._view()
        records = view.observation.public_discards[position]
        return [
            {
                "code": code_to_tile(tile),
                "used": used,
                "latest": (
                    position is view.last_discard_player
                    and index == len(records) - 1
                    and not used
                ),
            }
            for index, (tile, used) in enumerate(records)
        ]

    def _meld_tiles(self, position: PlayerPosition) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for kind, tile in self._observation().public_melds[position]:
            for _ in range(_MELD_SIZE.get(kind, 3)):
                result.append({"code": code_to_tile(tile) if tile is not None else "", "faceDown": tile is None})
        return result

    def _actions(self) -> list[dict[str, object]]:
        if len(self._action_map) == 1 and isinstance(next(iter(self._action_map.values())), PassAction):
            return []
        options: list[dict[str, object]] = []
        for key, action in self._action_map.items():
            if isinstance(action, (RonAction, TsumoAction)):
                label, color = "胡", "#c93228"
            elif isinstance(action, PengAction):
                label, color = "碰", "#d79220"
            elif isinstance(action, (ExposedGangAction, ConcealedGangAction, AddedGangAction)):
                label = "杠"
                color = "#cf7a20"
            elif isinstance(action, PassAction):
                label, color = "过", "#247e9b"
            else:
                continue
            options.append({"key": key, "label": label, "color": color})
        return options

    def _score(self, position: PlayerPosition) -> int:
        return self._view().scores[position]

    @Property("QVariantList", notify=stateChanged)
    def handTiles(self): return self._hand_tiles()

    @Property("QVariantList", notify=stateChanged)
    def selfDiscards(self): return self._discard_codes(PlayerPosition.SELF)

    @Property("QVariantList", notify=stateChanged)
    def leftDiscards(self): return self._discard_codes(PlayerPosition.LEFT)

    @Property("QVariantList", notify=stateChanged)
    def oppositeDiscards(self): return self._discard_codes(PlayerPosition.OPPOSITE)

    @Property("QVariantList", notify=stateChanged)
    def rightDiscards(self): return self._discard_codes(PlayerPosition.RIGHT)

    @Property("QVariantList", notify=stateChanged)
    def selfMelds(self): return self._meld_tiles(PlayerPosition.SELF)

    @Property("QVariantList", notify=stateChanged)
    def leftMelds(self): return self._meld_tiles(PlayerPosition.LEFT)

    @Property("QVariantList", notify=stateChanged)
    def oppositeMelds(self): return self._meld_tiles(PlayerPosition.OPPOSITE)

    @Property("QVariantList", notify=stateChanged)
    def rightMelds(self): return self._meld_tiles(PlayerPosition.RIGHT)

    @Property("QVariantList", notify=stateChanged)
    def actionOptions(self): return self._actions()

    @Property(int, notify=stateChanged)
    def selfConcealedCount(self): return self._observation().concealed_tile_counts[PlayerPosition.SELF]

    @Property(int, notify=stateChanged)
    def leftConcealedCount(self): return self._observation().concealed_tile_counts[PlayerPosition.LEFT]

    @Property(int, notify=stateChanged)
    def oppositeConcealedCount(self): return self._observation().concealed_tile_counts[PlayerPosition.OPPOSITE]

    @Property(int, notify=stateChanged)
    def rightConcealedCount(self): return self._observation().concealed_tile_counts[PlayerPosition.RIGHT]

    @Property(int, notify=stateChanged)
    def currentPlayer(self): return int(self._observation().current_player)

    @Property(int, notify=stateChanged)
    def dialSide(self):
        return {
            PlayerPosition.OPPOSITE: 0,
            PlayerPosition.LEFT: 1,
            PlayerPosition.RIGHT: 2,
            PlayerPosition.SELF: 3,
        }[self._observation().current_player]

    @Property(int, notify=stateChanged)
    def dealer(self): return int(self._view().dealer)

    @Property(int, notify=stateChanged)
    def wallRemaining(self): return self._observation().wall_remaining

    @Property(int, notify=stateChanged)
    def selfScore(self): return self._score(PlayerPosition.SELF)

    @Property(int, notify=stateChanged)
    def leftScore(self): return self._score(PlayerPosition.LEFT)

    @Property(int, notify=stateChanged)
    def oppositeScore(self): return self._score(PlayerPosition.OPPOSITE)

    @Property(int, notify=stateChanged)
    def rightScore(self): return self._score(PlayerPosition.RIGHT)

    @Property(bool, notify=stateChanged)
    def finished(self): return self._view().finished

    @Property(bool, notify=musicChanged)
    def musicEnabled(self): return self._music_enabled and self._music_player is not None

    @Property(str, notify=stateChanged)
    def statusText(self):
        view = self._view()
        if view.finished:
            if view.winner is None:
                return "本局流局"
            method = "自摸" if view.result == "tsumo" else "点炮"
            names = ("自己", "左家", "对家", "右家")
            return f"{names[int(view.winner)]} {method}"
        legal = self._legal()
        if len(legal) == 1 and isinstance(legal[0], PassAction):
            return "等待牌局继续…"
        if legal:
            return "轮到你：点击同一张手牌两次确认弃牌"
        return "AI 正在行动…"


def create_engine(app: QGuiApplication, *, seed: int | None = None) -> tuple[QQmlApplicationEngine, GameBridge]:
    bridge = GameBridge(seed=seed)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("gameBridge", bridge)
    qml_path = Path(__file__).with_name("qml") / "MahjongTablePreview.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise RuntimeError(f"无法加载 QML 游戏界面：{qml_path}")
    return engine, bridge


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine, bridge = create_engine(app)
    bridge.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
