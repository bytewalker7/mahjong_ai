import pytest

from mahjong_ai.meld import MeldType
from mahjong_ai.state import (
    AdvanceTurn, CallExposedGang, CallPeng, DeclareAddedGang,
    DeclareConcealedGang, DeclareWin, DiscardTile, DrawOwnTile, HiddenDraw,
    PlayerPosition, SetOwnInitialHand, StartRound, StateValidationError,
    apply_event, new_game, undo_last_event, validate_state,
)
from mahjong_ai.tiles import tile_to_code


SELF = PlayerPosition.SELF
LEFT = PlayerPosition.LEFT
OPPOSITE = PlayerPosition.OPPOSITE
RIGHT = PlayerPosition.RIGHT


def started_state() -> object:
    state = apply_event(new_game(), StartRound(SELF))
    hand = tuple(
        [tile_to_code("1w")]
        + [tile_to_code("2w")] * 4
        + [tile_to_code("3w")] * 4
        + [tile_to_code("4w")] * 4
        + [tile_to_code("5w")]
    )
    return apply_event(state, SetOwnInitialHand(hand))


def test_peng_moves_discard_into_meld_without_duplicate_visible_tile() -> None:
    state = started_state()
    state = apply_event(state, DiscardTile(SELF, tile_to_code("1w")))
    state = apply_event(state, CallPeng(RIGHT, tile_to_code("1w"), SELF))

    assert state.visible_counts[tile_to_code("1w")] == 3
    assert state.players[SELF].discards[0].called_by is RIGHT
    assert state.players[RIGHT].melds[0].meld_type is MeldType.PENG
    assert state.players[RIGHT].concealed_tile_count == 11
    validate_state(state)


def test_exposed_gang_consumes_last_discard_and_three_hidden_tiles() -> None:
    state = started_state()
    state = apply_event(state, DiscardTile(SELF, tile_to_code("1w")))
    state = apply_event(state, CallExposedGang(RIGHT, tile_to_code("1w"), SELF))

    assert state.visible_counts[tile_to_code("1w")] == 4
    assert state.players[RIGHT].concealed_tile_count == 10
    assert state.players[RIGHT].melds[0].meld_type is MeldType.EXPOSED_GANG


def test_concealed_and_added_gangs_update_counts_and_visibility() -> None:
    hand = tuple([tile_to_code("2w")] * 4 + [tile_to_code("3w")] + [tile_to_code("4w")] * 4 + [tile_to_code("5w")] * 4 + [tile_to_code("6w")])
    state = apply_event(new_game(), StartRound(SELF))
    state = apply_event(state, SetOwnInitialHand(hand))
    state = apply_event(state, DeclareConcealedGang(SELF, tile_to_code("2w")))
    assert state.players[SELF].concealed_tile_count == 10
    assert state.visible_counts[tile_to_code("2w")] == 0

    state = apply_event(state, DrawOwnTile(tile_to_code("6w")))
    state = apply_event(state, DiscardTile(SELF, tile_to_code("3w")))
    state = apply_event(state, CallPeng(RIGHT, tile_to_code("3w"), SELF))
    state = apply_event(state, HiddenDraw(RIGHT))
    # Other players are public-information only; their hidden tile identity is
    # not verified.  A later added gang still requires the existing peng.
    state = apply_event(state, DeclareAddedGang(RIGHT, tile_to_code("3w")))
    assert state.players[RIGHT].melds[0].meld_type is MeldType.ADDED_GANG
    assert state.visible_counts[tile_to_code("3w")] == 4


def test_undo_replays_to_exact_previous_state() -> None:
    state = started_state()
    before_discard = state
    state = apply_event(state, DiscardTile(SELF, tile_to_code("1w")))
    assert undo_last_event(state) == before_discard


def test_turn_and_call_source_validation() -> None:
    state = started_state()
    with pytest.raises(StateValidationError):
        apply_event(state, HiddenDraw(RIGHT))
    state = apply_event(state, DiscardTile(SELF, tile_to_code("1w")))
    with pytest.raises(StateValidationError):
        apply_event(state, CallPeng(RIGHT, tile_to_code("2w"), SELF))
    state = apply_event(state, AdvanceTurn(SELF))
    assert state.current_player is RIGHT


def test_win_finishes_round_and_rejects_later_actions() -> None:
    state = apply_event(started_state(), DeclareWin(SELF))
    assert state.round_finished is True
    with pytest.raises(StateValidationError):
        apply_event(state, DiscardTile(SELF, tile_to_code("1w")))


def test_rejects_public_tiles_that_would_exceed_four_copies() -> None:
    state = started_state()
    state = apply_event(state, DiscardTile(SELF, tile_to_code("2w")))
    state = apply_event(state, AdvanceTurn(SELF))
    state = apply_event(state, HiddenDraw(RIGHT))
    state = apply_event(state, DiscardTile(RIGHT, tile_to_code("6w")))
    state = apply_event(state, AdvanceTurn(RIGHT))
    state = apply_event(state, HiddenDraw(OPPOSITE))
    state = apply_event(state, DiscardTile(OPPOSITE, tile_to_code("6w")))
    state = apply_event(state, AdvanceTurn(OPPOSITE))
    state = apply_event(state, HiddenDraw(LEFT))
    state = apply_event(state, DiscardTile(LEFT, tile_to_code("1w")))
    with pytest.raises(StateValidationError):
        apply_event(state, CallExposedGang(RIGHT, tile_to_code("1w"), LEFT))
