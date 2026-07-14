"""An AI seat that is deliberately limited to its own public observation."""

from __future__ import annotations

from dataclasses import dataclass

from ..simulator.models import Action, Observation
from ..simulator.strategies import PlayerStrategy
from ..state.models import PlayerPosition


@dataclass
class AIPlayer:
    position: PlayerPosition
    strategy: PlayerStrategy

    def choose_action(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        """Delegate only the seat's own Observation and legal actions."""
        if observation.player is not self.position:
            raise ValueError("AI received an observation for a different seat")
        return self.strategy.choose_action(observation, legal_actions)
