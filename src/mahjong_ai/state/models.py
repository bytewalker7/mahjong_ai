"""Public-information state models for a four-player Mahjong round."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from ..meld import Meld, MeldType
from ..tiles import COPIES_PER_TILE, TILE_KIND_COUNT


class PlayerPosition(IntEnum):
    SELF = 0
    LEFT = 1
    OPPOSITE = 2
    RIGHT = 3

    def next_player(self) -> "PlayerPosition":
        """Return the next player in the configured turn order."""
        order = (PlayerPosition.SELF, PlayerPosition.RIGHT, PlayerPosition.OPPOSITE, PlayerPosition.LEFT)
        return order[(order.index(self) + 1) % len(order)]


@dataclass(frozen=True)
class RuleConfig:
    tile_kind_count: int = TILE_KIND_COUNT
    copies_per_tile: int = COPIES_PER_TILE
    player_count: int = 4
    allow_chi: bool = False
    allow_peng: bool = True
    allow_exposed_gang: bool = True
    allow_concealed_gang: bool = True
    allow_added_gang: bool = True

    @property
    def total_tiles(self) -> int:
        return self.tile_kind_count * self.copies_per_tile


@dataclass
class DiscardRecord:
    player: PlayerPosition
    tile: int
    called_by: PlayerPosition | None = None


@dataclass
class PlayerState:
    """Only the local player's concealed tiles are stored as actual tiles."""

    concealed_tile_count: int
    discards: list[DiscardRecord] = field(default_factory=list)
    melds: list[Meld] = field(default_factory=list)


@dataclass
class GameState:
    rules: RuleConfig
    own_hand: list[int]
    players: dict[PlayerPosition, PlayerState]
    current_player: PlayerPosition
    dealer: PlayerPosition
    wall_remaining: int
    last_discard: DiscardRecord | None
    visible_counts: list[int]
    events: list["GameEvent"]
    round_finished: bool = False


# Re-exported here to make the state model namespace convenient for consumers.
__all__ = [
    "DiscardRecord",
    "GameState",
    "Meld",
    "MeldType",
    "PlayerPosition",
    "PlayerState",
    "RuleConfig",
]
