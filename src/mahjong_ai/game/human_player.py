"""Human-seat validation kept separate from the UI."""

from __future__ import annotations

from ..simulator.models import Action, Observation
from ..state.models import PlayerPosition


class HumanPlayer:
    position = PlayerPosition.SELF

    def validate_action(self, observation: Observation, action: Action, legal_actions: tuple[Action, ...]) -> None:
        if observation.player is not self.position or observation.current_player is not self.position:
            raise ValueError("现在不是人类玩家的操作时机")
        if action not in legal_actions:
            raise ValueError("该人类操作不合法")
