import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from mahjong_ai.state import (
    AdvanceTurn, DiscardTile, HiddenDraw, PlayerPosition, SetOwnInitialHand,
    StartRound, apply_event, new_game,
)
from mahjong_ai.tiles import tile_to_code
from mahjong_ai.ui.main_window import MainWindow


def test_self_ron_button_accepts_a_valid_last_discard() -> None:
    app = QApplication.instance() or QApplication([])
    self_ = PlayerPosition.SELF
    right = PlayerPosition.RIGHT
    opposite = PlayerPosition.OPPOSITE
    left = PlayerPosition.LEFT
    state = apply_event(new_game(), StartRound(right))
    state = apply_event(state, SetOwnInitialHand(tuple(tile_to_code(tile) for tile in "2w 3w 4w 5w 5w 4s 5s 6s 8s 9s 5p 6p 7p".split())))
    state = apply_event(state, DiscardTile(right, tile_to_code("1w")))
    state = apply_event(state, AdvanceTurn(right))
    state = apply_event(state, HiddenDraw(opposite))
    state = apply_event(state, DiscardTile(opposite, tile_to_code("1s")))
    state = apply_event(state, AdvanceTurn(opposite))
    state = apply_event(state, HiddenDraw(left))
    state = apply_event(state, DiscardTile(left, tile_to_code("7s")))

    window = MainWindow()
    window.state = state
    window._refresh()
    buttons = [window.action_layout.itemAt(index).widget() for index in range(window.action_layout.count())]
    self_win = next(button for button in buttons if button.text() == "自己 胡")
    self_win.click()

    assert window.state.round_finished is True
    assert "本局已结束：自己胡牌" in window.context_label.text()
    assert window.action_layout.count() == 0
    window.close()
