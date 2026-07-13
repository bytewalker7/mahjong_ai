"""Data structures for completed open or concealed melds."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .tiles import TILE_KIND_COUNT, TileError


class MeldType(Enum):
    """The completed meld forms supported by the simplified rules."""

    PENG = "peng"
    EXPOSED_GANG = "exposed_gang"
    CONCEALED_GANG = "concealed_gang"
    ADDED_GANG = "added_gang"


@dataclass(frozen=True)
class Meld:
    """A completed triplet or quad.

    Every meld occupies exactly one of the four required winning-hand meld
    slots.  ``from_player`` records the discarder for calls; it is absent for
    concealed gangs and may be retained for an added gang's original peng.
    """

    meld_type: MeldType
    tile: int
    from_player: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.meld_type, MeldType):
            raise TypeError("meld_type must be a MeldType")
        if not 0 <= self.tile < TILE_KIND_COUNT:
            raise TileError(f"meld tile must be in 0..{TILE_KIND_COUNT - 1}")
        if self.from_player is not None and (not isinstance(self.from_player, int) or self.from_player < 0):
            raise ValueError("from_player must be a non-negative player index or None")
        if self.meld_type in (MeldType.PENG, MeldType.EXPOSED_GANG) and self.from_player is None:
            raise ValueError(f"{self.meld_type.value} requires from_player")
        if self.meld_type is MeldType.CONCEALED_GANG and self.from_player is not None:
            raise ValueError("concealed_gang must not have from_player")

    @property
    def tile_count(self) -> int:
        """Physical tile count of this meld (three for peng, four for gang)."""
        return 3 if self.meld_type is MeldType.PENG else 4


def validate_fixed_melds(fixed_melds: int) -> int:
    """Validate and return the number of already-completed melds."""
    if not isinstance(fixed_melds, int) or not 0 <= fixed_melds <= 4:
        raise ValueError("fixed_melds must be an integer in 0..4")
    return fixed_melds


def fixed_meld_count(melds: tuple[Meld, ...]) -> int:
    """Return a checked number of completed melds from concrete meld records."""
    for meld in melds:
        if not isinstance(meld, Meld):
            raise TypeError("melds must contain Meld instances")
    return validate_fixed_melds(len(melds))
