"""Pure hand-analysis API; this module has no command-line dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from .meld import Meld, fixed_meld_count, validate_fixed_melds
from .shanten import calculate_shanten
from .tiles import COPIES_PER_TILE, TILE_KIND_COUNT, code_to_tile, validate_counts


@dataclass(frozen=True)
class HandAnalysis:
    shanten: int
    winning_tiles: tuple[int, ...]
    effective_tiles: tuple[int, ...]
    remaining_by_tile: dict[int, int]

    @property
    def total_effective_tiles(self) -> int:
        return sum(self.remaining_by_tile[tile] for tile in self.effective_tiles)


@dataclass(frozen=True)
class DiscardAnalysis:
    discard: int
    analysis: HandAnalysis


def _remaining_counts(hand: list[int], visible: list[int], melds: Sequence[Meld]) -> list[int]:
    meld_tiles = [0] * TILE_KIND_COUNT
    for meld in melds:
        meld_tiles[meld.tile] += meld.tile_count
    remaining = [COPIES_PER_TILE - hand[tile] - visible[tile] - meld_tiles[tile] for tile in range(TILE_KIND_COUNT)]
    if any(number < 0 for number in remaining):
        raise ValueError("hand and visible tiles together contain more than four copies of a tile")
    return remaining


def analyze_hand(
    hand_counts: list[int],
    visible_counts: list[int] | None = None,
    *,
    fixed_melds: int = 0,
    melds: Sequence[Meld] = (),
) -> HandAnalysis:
    """Analyse a concealed hand, optionally with completed fixed melds.

    Concrete ``melds`` automatically reduce tile availability. When they are
    supplied, their number must match ``fixed_melds`` unless the latter uses
    its default zero value, in which case it is inferred from ``melds``.
    With only ``fixed_melds``, callers must include known meld tiles in
    ``visible_counts`` if they need exact remaining-tile counts.
    """
    hand = validate_counts(hand_counts)
    visible = validate_counts(visible_counts or [0] * TILE_KIND_COUNT)
    concrete_melds = tuple(melds)
    meld_count = fixed_meld_count(concrete_melds)
    fixed_melds = validate_fixed_melds(fixed_melds)
    if concrete_melds and fixed_melds not in (0, meld_count):
        raise ValueError("fixed_melds must match the number of supplied melds")
    fixed_melds = meld_count if concrete_melds else fixed_melds
    base_shanten = calculate_shanten(hand, fixed_melds)
    remaining = _remaining_counts(hand, visible, concrete_melds)
    winning: list[int] = []
    effective: list[int] = []
    for tile, copies_left in enumerate(remaining):
        if copies_left == 0:
            continue
        hand[tile] += 1
        next_shanten = calculate_shanten(hand, fixed_melds)
        hand[tile] -= 1
        if base_shanten == 0 and next_shanten == -1:
            winning.append(tile)
        if next_shanten < base_shanten:
            effective.append(tile)
    return HandAnalysis(base_shanten, tuple(winning), tuple(effective), {tile: remaining[tile] for tile in range(TILE_KIND_COUNT)})


def analyze_discards(
    hand_counts: list[int],
    visible_counts: list[int] | None = None,
    *,
    fixed_melds: int = 0,
    melds: Sequence[Meld] = (),
) -> tuple[DiscardAnalysis, ...]:
    """Analyse every distinct discard, ordered by recommendation quality.

    A lower resulting shanten is preferred; ties favour more remaining effective
    tiles, then the lower internal tile code for deterministic output.
    """
    hand = validate_counts(hand_counts)
    visible = validate_counts(visible_counts or [0] * TILE_KIND_COUNT)
    concrete_melds = tuple(melds)
    meld_count = fixed_meld_count(concrete_melds)
    fixed_melds = validate_fixed_melds(fixed_melds)
    if concrete_melds and fixed_melds not in (0, meld_count):
        raise ValueError("fixed_melds must match the number of supplied melds")
    fixed_melds = meld_count if concrete_melds else fixed_melds
    candidates: list[DiscardAnalysis] = []
    for tile, count in enumerate(hand):
        if not count:
            continue
        hand[tile] -= 1
        candidates.append(DiscardAnalysis(tile, analyze_hand(hand, visible, fixed_melds=fixed_melds, melds=concrete_melds)))
        hand[tile] += 1
    return tuple(sorted(candidates, key=lambda item: (item.analysis.shanten, -item.analysis.total_effective_tiles, item.discard)))


def format_tiles(tiles: tuple[int, ...]) -> str:
    """Format tile codes for a human-facing adapter such as the CLI."""
    return " ".join(code_to_tile(tile) for tile in tiles) or "无"
