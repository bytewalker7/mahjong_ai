"""Public-observation single-agent wrapper around the existing simulator."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

from ..simulator.environment import MahjongEnvironment
from ..simulator.models import Action, DiscardAction, Observation, Phase, RonAction, TsumoAction
from ..simulator.strategies import HeuristicPlayer, NoisyHeuristicPlayer, PlayerStrategy, RandomPlayer
from ..state.models import PlayerPosition
from ..tiles import TILE_KIND_COUNT


@dataclass(frozen=True)
class RLStep:
    features: tuple[float, ...]
    legal_mask: tuple[bool, ...]
    reward: float
    done: bool
    observation: Observation
    score: int


class DiscardRLEnvironment:
    """Train SELF's discard choices using observation-only automatic players.

    Opponents and SELF's non-discard choices receive only their own Observation.
    This keeps the single-agent wrapper fair while allowing a curriculum that
    produces substantially more informative completed rounds than random play.
    """

    feature_version = "discard_features_v2"
    feature_size = 441

    def __init__(
        self,
        randomize_pao: bool = False,
        opponent_mode: Literal["random", "noisy", "heuristic", "curriculum"] = "random",
    ) -> None:
        # Full-information dataset snapshots calculate all four players'
        # shanten and waits after every event. RL needs none of those hidden
        # labels, so disabling them is both faster and stricter about leakage.
        self.simulator = MahjongEnvironment(record_full_snapshots=False)
        self.randomize_pao = randomize_pao
        self.opponent_mode = opponent_mode
        self.rng = random.Random()
        self._automatic_players: dict[PlayerPosition, PlayerStrategy] = {}

    def reset(self, seed: int | None = None) -> RLStep:
        self.rng = random.Random(seed)
        pao = {position: self.rng.randrange(5) for position in PlayerPosition} if self.randomize_pao else {position: 0 for position in PlayerPosition}
        self.simulator.reset(seed, pao)
        self._automatic_players = {
            position: self._make_automatic_player(position)
            for position in PlayerPosition
        }
        return self._advance_until_decision(0.0)

    def step(self, discard_tile: int) -> RLStep:
        legal = self.simulator.legal_actions()
        action = DiscardAction(discard_tile)
        if action not in legal or self.simulator.full_state.current_player is not PlayerPosition.SELF:
            raise ValueError("discard is not a legal SELF action")
        before = self.simulator.full_state.scores[PlayerPosition.SELF]
        self.simulator.step(action)
        return self._advance_until_decision(float(self.simulator.full_state.scores[PlayerPosition.SELF] - before))

    def _advance_until_decision(self, reward: float) -> RLStep:
        before = self.simulator.full_state.scores[PlayerPosition.SELF]
        while self.simulator.full_state.phase is not Phase.FINISHED:
            state = self.simulator.full_state
            legal = self.simulator.legal_actions()
            if state.current_player is PlayerPosition.SELF and state.phase is Phase.DISCARD:
                # Never train a discard choice in a state where winning is legal.
                winning = next((action for action in legal if isinstance(action, TsumoAction)), None)
                if winning is None:
                    observation = self.simulator.observation(PlayerPosition.SELF)
                    return RLStep(self.encode(observation), self.mask(observation), reward + state.scores[PlayerPosition.SELF] - before, False, observation, state.scores[PlayerPosition.SELF])
                self.simulator.step(winning)
                continue
            self.simulator.step(self._automatic_action(state.current_player, legal))
        observation = self.simulator.observation(PlayerPosition.SELF)
        score = self.simulator.full_state.scores[PlayerPosition.SELF]
        return RLStep(self.encode(observation), (False,) * TILE_KIND_COUNT, reward + score - before, True, observation, score)

    def _automatic_action(self, player: PlayerPosition, legal: tuple[Action, ...]) -> Action:
        winning = next((action for action in legal if isinstance(action, (RonAction, TsumoAction))), None)
        if winning is not None:
            return winning
        observation = self.simulator.observation(player)
        return self._automatic_players[player].choose_action(observation, legal)

    def _make_automatic_player(self, position: PlayerPosition) -> PlayerStrategy:
        seed = self.rng.randrange(2**63) ^ (int(position) << 16)
        if self.opponent_mode == "heuristic":
            return HeuristicPlayer(seed)
        if self.opponent_mode == "noisy":
            return NoisyHeuristicPlayer(seed, temperature=1.0)
        if self.opponent_mode == "curriculum":
            choice = self.rng.random()
            if choice < 0.25:
                return RandomPlayer(seed)
            if choice < 0.75:
                return NoisyHeuristicPlayer(seed, temperature=self.rng.uniform(0.5, 1.5))
            return HeuristicPlayer(seed)
        return RandomPlayer(seed)

    @staticmethod
    def mask(observation: Observation) -> tuple[bool, ...]:
        return tuple(count > 0 for count in observation.own_hand)

    @staticmethod
    def encode(observation: Observation) -> tuple[float, ...]:
        """Public-only tile channels with discard order and meld information."""
        own = [count / 4.0 for count in observation.own_hand]
        visible = [count / 4.0 for count in observation.visible_counts]
        concealed = [count / 14.0 for count in observation.concealed_tile_counts]
        discard_counts: list[float] = []
        recent_discards: list[float] = []
        for discards in observation.public_discards:
            counts = [0.0] * TILE_KIND_COUNT
            for tile, _called in discards:
                counts[tile] += 0.25
            discard_counts.extend(counts)
            recent = [0.0] * (TILE_KIND_COUNT + 1)
            recent[discards[-1][0] if discards else TILE_KIND_COUNT] = 1.0
            recent_discards.extend(recent)

        meld_tiles: list[float] = []
        meld_types: list[float] = []
        type_order = ("peng", "exposed_gang", "concealed_gang", "added_gang")
        for melds in observation.public_melds:
            tiles = [0.0] * TILE_KIND_COUNT
            types = [0.0] * len(type_order)
            for meld_type, tile in melds:
                types[type_order.index(meld_type)] += 0.25
                if tile is not None:
                    tiles[tile] += 0.25
            meld_tiles.extend(tiles)
            meld_types.extend(types)

        dealer = [float(observation.dealer is position) for position in PlayerPosition]
        last_discard = [0.0] * (TILE_KIND_COUNT + 1)
        last_discard[observation.last_discard_tile if observation.last_discard_tile is not None else TILE_KIND_COUNT] = 1.0
        phases = [float(observation.phase is phase) for phase in Phase]
        encoded = own + visible + concealed + discard_counts + recent_discards + meld_tiles + meld_types + dealer + last_discard + phases + [
            observation.wall_remaining / 55.0,
            min(observation.turn, 100) / 100.0,
        ]
        if len(encoded) != DiscardRLEnvironment.feature_size:
            raise AssertionError(f"unexpected RL feature size: {len(encoded)}")
        return tuple(encoded)

    @staticmethod
    def encode_v1(observation: Observation) -> tuple[float, ...]:
        """Legacy 60-feature encoder for evaluating existing v0.7 models."""
        own = [count / 4.0 for count in observation.own_hand]
        visible = [count / 4.0 for count in observation.visible_counts]
        concealed = [count / 14.0 for count in observation.concealed_tile_counts]
        return tuple(own + visible + concealed + [observation.wall_remaining / 55.0, min(observation.turn, 100) / 100.0])
