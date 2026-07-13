from __future__ import annotations

from mahjong_ai.risk.observation import observation_from_dict, observation_from_game_state, observation_to_dict
from mahjong_ai.state import DiscardTile, PlayerPosition, SetOwnInitialHand, StartRound, apply_event, new_game


def test_game_state_observation_is_public_and_json_round_trips() -> None:
    state = apply_event(new_game(), StartRound(PlayerPosition.SELF))
    tiles = tuple([0] * 4 + [1] * 4 + [2] * 4 + [3] * 2)
    state = apply_event(state, SetOwnInitialHand(tiles))
    observation = observation_from_game_state(state)
    assert observation.current_player is PlayerPosition.SELF
    assert observation.phase.value == "discard"
    assert observation.own_hand[0] == 4
    assert observation_from_dict(observation_to_dict(observation)) == observation


def test_called_discard_is_exported_as_used_public_tile() -> None:
    state = apply_event(new_game(), StartRound(PlayerPosition.SELF))
    tiles = tuple([0] * 4 + [1] * 4 + [2] * 4 + [3] * 2)
    state = apply_event(state, SetOwnInitialHand(tiles))
    state = apply_event(state, DiscardTile(PlayerPosition.SELF, 3))
    observation = observation_from_game_state(state)
    assert observation.phase.value == "response"
    assert observation.public_discards[PlayerPosition.SELF][-1] == (3, False)
