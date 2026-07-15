from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QSG_RHI_BACKEND", "software")

from PySide6.QtGui import QGuiApplication

from mahjong_ai.simulator.models import DiscardAction
from mahjong_ai.state.models import PlayerPosition
from mahjong_ai.ui.qml_game import GameBridge, _find_background_music, create_engine


def _app() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


def _advance_to_human_discard(bridge: GameBridge) -> None:
    for _ in range(1000):
        legal = bridge.session.human_legal_actions()
        if any(isinstance(action, DiscardAction) for action in legal):
            bridge._emit_state()
            return
        if bridge.session.view().finished:
            raise AssertionError("game ended before a human discard")
        if not bridge.session.advance_automatic_step():
            raise AssertionError("session stopped before a human discard")
    raise AssertionError("no human discard found")


def test_qml_bridge_two_click_discard_and_public_hand_only() -> None:
    _app()
    bridge = GameBridge(seed=42)
    _advance_to_human_discard(bridge)
    hand = bridge.handTiles
    assert sum(1 for item in hand if item["drawn"]) <= 1
    assert bridge.leftConcealedCount >= 0
    assert not hasattr(bridge, "leftHand")
    tile = next(action.tile for action in bridge.session.human_legal_actions() if isinstance(action, DiscardAction))
    before = len(bridge.session.environment.full_state.events)
    bridge.clickTile(tile)
    selected = [item for item in bridge.handTiles if item["selected"]]
    assert len(selected) == 1
    assert selected[0]["tile"] == tile
    assert len(bridge.session.environment.full_state.events) == before
    bridge.clickTile(tile)
    assert len(bridge.session.environment.full_state.events) > before
    assert code_in_discards(tile, bridge.selfDiscards)


def code_in_discards(tile: int, records: list[dict[str, object]]) -> bool:
    suffix = ("w", "s", "p")[tile // 9]
    return f"{tile % 9 + 1}{suffix}" in [record["code"] for record in records]


def test_latest_discard_is_marked_once() -> None:
    _app()
    bridge = GameBridge(seed=42)
    _advance_to_human_discard(bridge)
    tile = next(action.tile for action in bridge.session.human_legal_actions() if isinstance(action, DiscardAction))
    bridge.clickTile(tile)
    bridge.clickTile(tile)
    assert sum(bool(record["latest"]) for record in bridge.selfDiscards) == 1


def test_music_toggle_changes_bridge_property_when_audio_is_available() -> None:
    _app()
    bridge = GameBridge(seed=9)
    if bridge._music_player is None:
        return
    assert bridge.musicEnabled
    bridge.toggleMusic()
    assert not bridge.musicEnabled
    bridge.toggleMusic()
    assert bridge.musicEnabled


def test_background_music_prefers_wav_and_keeps_mp3_fallback(tmp_path) -> None:
    mp3 = tmp_path / "background music.mp3"
    wav = tmp_path / "background music.wav"
    mp3.write_bytes(b"mp3")
    assert _find_background_music(tmp_path) == mp3
    wav.write_bytes(b"wav")
    assert _find_background_music(tmp_path) == wav


def test_qml_window_loads_with_real_public_state() -> None:
    app = _app()
    engine, bridge = create_engine(app, seed=7)
    bridge.start()
    app.processEvents()
    roots = engine.rootObjects()
    assert len(roots) == 1
    assert len(bridge.handTiles) in {13, 14}
    assert bridge.currentPlayer in tuple(int(position) for position in PlayerPosition)
    roots[0].close()
