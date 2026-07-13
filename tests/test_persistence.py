from mahjong_ai.persistence import load_state, save_state
from mahjong_ai.state import DiscardTile, PlayerPosition, SetOwnInitialHand, StartRound, apply_event, new_game
from mahjong_ai.tiles import tile_to_code


def test_save_and_load_replays_identical_event_state(tmp_path) -> None:
    state = apply_event(new_game(), StartRound(PlayerPosition.SELF))
    tiles = tuple(
        [tile_to_code("1w")]
        + [tile_to_code("2w")] * 4
        + [tile_to_code("3w")] * 4
        + [tile_to_code("4w")] * 4
        + [tile_to_code("5w")]
    )
    state = apply_event(state, SetOwnInitialHand(tiles))
    state = apply_event(state, DiscardTile(PlayerPosition.SELF, tile_to_code("1w")))
    path = tmp_path / "round.json"
    save_state(path, state)
    assert load_state(path) == state
