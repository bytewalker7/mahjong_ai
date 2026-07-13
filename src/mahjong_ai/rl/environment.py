"""Public-observation single-agent wrapper around the existing simulator."""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..simulator.environment import MahjongEnvironment
from ..simulator.models import Action, DiscardAction, Observation, Phase, RonAction, TsumoAction
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
    """Train SELF's discard choices; all non-discard decisions use random play.

    The internal players never use HeuristicPlayer.  They only see their own
    Observation and legal actions, and prioritize an already-legal win.
    """

    feature_size = 60

    def __init__(self, randomize_pao: bool = False) -> None:
        self.simulator = MahjongEnvironment()
        self.randomize_pao = randomize_pao
        self.rng = random.Random()

    def reset(self, seed: int | None = None) -> RLStep:
        self.rng = random.Random(seed)
        pao = {position: self.rng.randrange(5) for position in PlayerPosition} if self.randomize_pao else {position: 0 for position in PlayerPosition}
        self.simulator.reset(seed, pao)
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
            self.simulator.step(self._random_legal_action(legal))
        observation = self.simulator.observation(PlayerPosition.SELF)
        score = self.simulator.full_state.scores[PlayerPosition.SELF]
        return RLStep(self.encode(observation), (False,) * TILE_KIND_COUNT, reward + score - before, True, observation, score)

    def _random_legal_action(self, legal: tuple[Action, ...]) -> Action:
        winning = next((action for action in legal if isinstance(action, (RonAction, TsumoAction))), None)
        return winning if winning is not None else self.rng.choice(legal)

    @staticmethod
    def mask(observation: Observation) -> tuple[bool, ...]:
        return tuple(count > 0 for count in observation.own_hand)

    @staticmethod
    def encode(observation: Observation) -> tuple[float, ...]:
        """60 public/legal features: own hand, visible tiles, counts, clock."""
        own = [count / 4.0 for count in observation.own_hand]
        visible = [count / 4.0 for count in observation.visible_counts]
        concealed = [count / 14.0 for count in observation.concealed_tile_counts]
        return tuple(own + visible + concealed + [observation.wall_remaining / 55.0, min(observation.turn, 100) / 100.0])
