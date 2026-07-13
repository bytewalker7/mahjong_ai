"""Settlement rules from :mod:`rules.markdown` for the simplified table."""

from __future__ import annotations

from dataclasses import dataclass

from ..meld import MeldType
from ..state.models import PlayerPosition


@dataclass(frozen=True)
class ScoreRules:
    """Explicit, configurable point values copied from ``rules.markdown``."""

    ron_points: int = 1
    tsumo_payment: int = 2
    concealed_gang_points: int = 2
    exposed_gang_points: int = 1
    added_gang_points: int = 1
    dealer_hu_multiplier: int = 2
    max_pao_count: int = 4

    def gang_points(self, meld_type: MeldType) -> int:
        return {
            MeldType.CONCEALED_GANG: self.concealed_gang_points,
            MeldType.EXPOSED_GANG: self.exposed_gang_points,
            MeldType.ADDED_GANG: self.added_gang_points,
        }[meld_type]


def empty_scores() -> dict[PlayerPosition, int]:
    return {position: 0 for position in PlayerPosition}
