"""Baseline policies that consume only legal observations and actions."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ..shanten import calculate_shanten
from ..tiles import COPIES_PER_TILE
from .models import (
    Action, AddedGangAction, ConcealedGangAction, DiscardAction, ExposedGangAction,
    Observation, PassAction, PengAction, RonAction, TsumoAction,
)


class PlayerStrategy:
    def choose_action(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        raise NotImplementedError


@dataclass
class RandomPlayer(PlayerStrategy):
    seed: int | None = None

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def choose_action(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        return self.rng.choice(legal_actions)


@dataclass
class HeuristicPlayer(PlayerStrategy):
    """Strict shanten/ukeire discard policy with explicit simple call rules."""

    seed: int | None = None

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def choose_action(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        for action in legal_actions:
            if isinstance(action, (TsumoAction, RonAction, ConcealedGangAction, AddedGangAction, ExposedGangAction)):
                return action
        discards = [action for action in legal_actions if isinstance(action, DiscardAction)]
        if discards:
            return DiscardAction(self._rank_discards(observation)[0][0])
        peng = next((action for action in legal_actions if isinstance(action, PengAction)), None)
        if peng is not None and self._should_peng(observation):
            return peng
        return next(action for action in legal_actions if isinstance(action, PassAction)) if any(isinstance(action, PassAction) for action in legal_actions) else legal_actions[0]

    def _should_peng(self, observation: Observation) -> bool:
        # During a response the last discard is encoded as the final live
        # discard in public data. Compare the current hand with opening that
        # triplet; only accept if shanten improves or strict ukeire increases.
        if observation.last_discard_tile is None:
            return False
        tile = observation.last_discard_tile
        before_shanten = calculate_shanten(list(observation.own_hand), len(observation.own_melds))
        hand = list(observation.own_hand)
        hand[tile] -= 2
        after_shanten = calculate_shanten(hand, len(observation.own_melds) + 1)
        return after_shanten < before_shanten

    def _rank_discards(self, observation: Observation) -> list[tuple[int, int, int, int]]:
        """Rank discards with strict shanten then strict ukeire, without leaks."""
        hand = list(observation.own_hand)
        visible = list(observation.visible_counts)
        fixed = len(observation.own_melds)
        shanten_by_tile: dict[int, int] = {}
        for tile, count in enumerate(hand):
            if count:
                hand[tile] -= 1
                shanten_by_tile[tile] = calculate_shanten(hand, fixed)
                hand[tile] += 1
        best_shanten = min(shanten_by_tile.values())
        ranked: list[tuple[int, int, int, int]] = []
        for discard, shanten in shanten_by_tile.items():
            if shanten != best_shanten:
                ranked.append((discard, shanten, 0, 0))
                continue
            hand[discard] -= 1
            visible[discard] += 1
            effective: list[int] = []
            total = 0
            for draw in range(len(hand)):
                remaining = COPIES_PER_TILE - hand[draw] - visible[draw]
                if remaining <= 0:
                    continue
                hand[draw] += 1
                if calculate_shanten(hand, fixed) < shanten:
                    effective.append(draw)
                    total += remaining
                hand[draw] -= 1
            visible[discard] -= 1
            hand[discard] += 1
            ranked.append((discard, shanten, total, len(effective)))
        return sorted(ranked, key=lambda item: (item[1], -item[2], -item[3], item[0]))


@dataclass
class NoisyHeuristicPlayer(HeuristicPlayer):
    temperature: float = 1.0

    def choose_action(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        # Ranking a discard calculates shanten and ukeire for every candidate.
        # Compute it once per decision rather than once per legal action.
        ranked = self._rank_discards(observation) if any(isinstance(action, DiscardAction) for action in legal_actions) else None
        scores = [self._score_action(observation, action, ranked) for action in legal_actions]
        temperature = max(self.temperature, 0.05)
        maximum = max(scores)
        weights = [math.exp((score - maximum) / temperature) for score in scores]
        return self.rng.choices(list(legal_actions), weights=weights, k=1)[0]

    def _score_action(
        self,
        observation: Observation,
        action: Action,
        ranked: list[tuple[int, int, int, int]] | None = None,
    ) -> float:
        if isinstance(action, (TsumoAction, RonAction)):
            return 1_000.0
        if isinstance(action, (ConcealedGangAction, AddedGangAction, ExposedGangAction)):
            return 40.0
        if isinstance(action, PengAction):
            return 15.0 if self._should_peng(observation) else -15.0
        if isinstance(action, PassAction):
            return 0.0
        if isinstance(action, DiscardAction):
            ranked = ranked if ranked is not None else self._rank_discards(observation)
            rank = next(index for index, candidate in enumerate(ranked) if candidate[0] == action.tile)
            _tile, shanten, total, kinds = ranked[rank]
            return -shanten * 100 + total * 3 + kinds - rank * 0.01
        return 5.0
