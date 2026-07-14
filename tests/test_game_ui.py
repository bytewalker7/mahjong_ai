from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from mahjong_ai.game.session import GameSession
from mahjong_ai.simulator.models import DiscardAction, PengAction, RonAction, TsumoAction
from mahjong_ai.simulator.strategies import RandomPlayer
from mahjong_ai.state.models import PlayerPosition
from mahjong_ai.ui.game_window import GameWindow


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _session(seed: int = 77) -> GameSession:
    return GameSession(seed=seed, strategies={
        PlayerPosition.LEFT: RandomPlayer(1), PlayerPosition.OPPOSITE: RandomPlayer(2), PlayerPosition.RIGHT: RandomPlayer(3),
    })


def _human_decision(session: GameSession) -> None:
    for _ in range(500):
        while session.advance_automatic_step():
            pass
        legal = session.human_legal_actions()
        if any(isinstance(action, DiscardAction) for action in legal):
            return
        if legal:
            session.apply_human_action(next((action for action in legal if isinstance(action, (RonAction, TsumoAction))), legal[0]))
            continue
        if session.view().finished:
            raise AssertionError("session finished before a human discard decision")
        raise AssertionError("session stopped without a human decision")
    raise AssertionError("no human decision")


def _window_at_human_decision() -> GameWindow:
    _app(); window = GameWindow(); window.timer.stop(); window.session = _session(); _human_decision(window.session); window._refresh()
    return window


def test_first_and_second_tile_click_selection_behavior() -> None:
    window = _window_at_human_decision()
    tile = next(action.tile for action in window.session.human_legal_actions() if isinstance(action, DiscardAction))
    before = len(window.session.environment.full_state.events)
    window._hand_tile_clicked(tile)
    assert window.selected_tile == tile
    assert len(window.session.environment.full_state.events) == before
    window._hand_tile_clicked(tile)
    assert window.selected_tile is None
    assert len(window.session.environment.full_state.events) > before
    assert any(event["kind"] == "discard" and event["player"] == "SELF" and event["tile"] == tile for event in window.session.environment.full_state.events[before:])


def test_clicking_another_tile_switches_selection_without_discard() -> None:
    window = _window_at_human_decision()
    tiles = [action.tile for action in window.session.human_legal_actions() if isinstance(action, DiscardAction)]
    assert len(set(tiles)) >= 2
    before = len(window.session.environment.full_state.events)
    window._hand_tile_clicked(tiles[0]); window._hand_tile_clicked(next(tile for tile in tiles if tile != tiles[0]))
    assert window.selected_tile != tiles[0]
    assert len(window.session.environment.full_state.events) == before


def test_non_human_phase_cannot_discard_and_actions_match_legal_actions() -> None:
    _app(); window = GameWindow(); window.timer.stop(); window.session = _session(91); window._refresh()
    before = len(window.session.environment.full_state.events)
    window._hand_tile_clicked(0)
    assert len(window.session.environment.full_state.events) == before
    _human_decision(window.session); window._refresh()
    legal = window.session.human_legal_actions()
    labels = {button.text()[0] for button in window._action_buttons}
    assert ("胡" in labels) == any(isinstance(action, (RonAction, TsumoAction)) for action in legal)
    assert ("碰" in labels) == any(isinstance(action, PengAction) for action in legal)
    assert window.table.indicator.current is window.session.view().observation.current_player


def test_human_drawn_tile_is_separated_at_right_and_ai_hands_are_not_widgets() -> None:
    window = _window_at_human_decision()
    for _ in range(100):
        if window.session.view().drawn_tile is not None:
            break
        legal = window.session.human_legal_actions()
        discard = next((action for action in legal if isinstance(action, DiscardAction)), None)
        window.session.apply_human_action(discard or legal[0]); _human_decision(window.session)
    window._refresh()
    assert window.session.view().drawn_tile is not None
    widgets = window.table.hand_widgets
    assert widgets[-1].tile == window.session.view().drawn_tile
    assert widgets[-1].x() - widgets[-2].x() > widgets[-2].width()
    assert all(widget.tile in range(27) for widget in widgets)
