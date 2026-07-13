from copy import deepcopy

from mahjong_ai.dataset import extract_samples
from mahjong_ai.simulator.environment import MahjongEnvironment
from mahjong_ai.simulator.logging import replay_full_log
from mahjong_ai.simulator.runner import simulate_game
from mahjong_ai.simulator.strategies import RandomPlayer
from mahjong_ai.state.models import PlayerPosition
from mahjong_ai.tiles import TILE_KIND_COUNT


def test_environment_conserves_all_tiles_with_random_legal_actions() -> None:
    environment = MahjongEnvironment()
    environment.reset(123)
    player = RandomPlayer(456)
    while environment.legal_actions():
        position = environment.full_state.current_player
        environment.step(player.choose_action(environment.observation(position), environment.legal_actions()))
        environment._validate()
    assert environment.full_state.result in {"draw", "ron", "tsumo"}


def test_observation_does_not_contain_other_hidden_hands() -> None:
    environment = MahjongEnvironment()
    observation = environment.reset(1)
    assert not hasattr(observation, "full_state")
    assert not hasattr(observation, "other_hands")
    assert len(observation.own_hand) == TILE_KIND_COUNT


def test_same_seed_replays_exactly_and_different_seed_changes_game() -> None:
    first = simulate_game(17)
    second = simulate_game(17)
    third = simulate_game(18)
    assert first == second
    assert first["initial_hands"] != third["initial_hands"] or first["wall_order"] != third["wall_order"]
    replay = replay_full_log(first)
    assert replay.full_state.result == first["final_result"]


def test_dataset_features_do_not_include_target_hidden_hand_or_mutate_log() -> None:
    log = simulate_game(29)
    original = deepcopy(log)
    samples = extract_samples(log)
    assert samples
    assert log == original
    sample = samples[0]
    assert "target_hand" not in sample.public_input
    assert sample.target != sample.observer
    assert all(item.game_id == log["game_id"] for item in samples[:3])
    assert sample.target_is_tenpai == (sample.target_shanten == 0)
    assert len(sample.target_wait_mask) == TILE_KIND_COUNT
    assert len(sample.target_danger_mask) == TILE_KIND_COUNT
    snapshot = log["events"][sample.event_index]["snapshot"]
    expected_waits = set(snapshot["waits"][sample.target])
    assert sample.target_wait_mask == tuple(tile in expected_waits for tile in range(TILE_KIND_COUNT))
    assert snapshot["is_tenpai"][sample.target] == (snapshot["shanten"][sample.target] == 0)
