"""Batch simulator orchestration with deterministic strategy assignment."""

from __future__ import annotations

import random

from ..state.models import PlayerPosition
from .environment import MahjongEnvironment
from .logging import action_to_dict
from .strategies import HeuristicPlayer, NoisyHeuristicPlayer, PlayerStrategy, RandomPlayer


def random_strategies(seed: int) -> dict[PlayerPosition, PlayerStrategy]:
    rng = random.Random(seed)
    result: dict[PlayerPosition, PlayerStrategy] = {}
    for position in PlayerPosition:
        kind = rng.choice(("random", "heuristic", "noisy"))
        strategy_seed = rng.randrange(2**63)
        if kind == "random":
            result[position] = RandomPlayer(strategy_seed)
        elif kind == "heuristic":
            result[position] = HeuristicPlayer(strategy_seed)
        else:
            result[position] = NoisyHeuristicPlayer(strategy_seed, temperature=rng.uniform(0.35, 2.0))
    return result


def simulate_game(seed: int, game_id: str | None = None, strategies: dict[PlayerPosition, PlayerStrategy] | None = None) -> dict[str, object]:
    environment = MahjongEnvironment()
    environment.reset(seed)
    state = environment.full_state
    initial_hands = {position.name: player.hand.copy() for position, player in state.players.items()}
    wall_order = state.wall.copy()
    players = strategies or random_strategies(seed ^ 0x5EED)
    actions: list[dict[str, object]] = []
    maximum_steps = 10_000
    while environment.full_state.phase.value != "finished" and len(actions) < maximum_steps:
        position = environment.full_state.current_player
        observation = environment.observation(position)
        legal = environment.legal_actions()
        action = players[position].choose_action(observation, legal)
        actions.append(action_to_dict(action))
        environment.step(action)
    if environment.full_state.phase.value != "finished":
        raise RuntimeError("simulator exceeded action safety limit")
    final = environment.full_state
    return {
        "game_id": game_id or f"game-{seed}",
        "seed": seed,
        "rule_version": "simplified-108-v1",
        "dealer": final.dealer.name,
        "initial_hands": initial_hands,
        "wall_order": wall_order,
        "strategy_assignment": {
            position.name: {
                "type": type(strategy).__name__,
                "seed": getattr(strategy, "seed", None),
                "temperature": getattr(strategy, "temperature", None),
            }
            for position, strategy in players.items()
        },
        "actions": actions,
        "events": final.events,
        "winner": final.winner.name if final.winner is not None else None,
        "final_result": final.result,
    }
