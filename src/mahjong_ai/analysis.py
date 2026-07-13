"""Pure hand-analysis API; this module has no command-line dependencies."""

from __future__ import annotations

from dataclasses import dataclass

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


def _remaining_counts(hand: list[int], visible: list[int]) -> list[int]:
    remaining = [COPIES_PER_TILE - hand[tile] - visible[tile] for tile in range(TILE_KIND_COUNT)]
    if any(number < 0 for number in remaining):
        raise ValueError("hand and visible tiles together contain more than four copies of a tile")
    return remaining


def analyze_hand(hand_counts: list[int], visible_counts: list[int] | None = None) -> HandAnalysis:
    """Analyse one hand and return shanten, waits, improving draws, and availability."""
    hand = validate_counts(hand_counts)
    visible = validate_counts(visible_counts or [0] * TILE_KIND_COUNT)
    base_shanten = calculate_shanten(hand)
    remaining = _remaining_counts(hand, visible)
    winning: list[int] = []
    effective: list[int] = []
    for tile, copies_left in enumerate(remaining):
        if copies_left == 0:
            continue
        hand[tile] += 1
        next_shanten = calculate_shanten(hand)
        hand[tile] -= 1
        if base_shanten == 0 and next_shanten == -1:
            winning.append(tile)
        if next_shanten < base_shanten:
            effective.append(tile)
    return HandAnalysis(base_shanten, tuple(winning), tuple(effective), {tile: remaining[tile] for tile in range(TILE_KIND_COUNT)})


def analyze_discards(hand_counts: list[int], visible_counts: list[int] | None = None) -> tuple[DiscardAnalysis, ...]:
    """Analyse every distinct discard, ordered by recommendation quality.

    A lower resulting shanten is preferred; ties favour more remaining effective
    tiles, then the lower internal tile code for deterministic output.
    """
    hand = validate_counts(hand_counts)
    visible = validate_counts(visible_counts or [0] * TILE_KIND_COUNT)
    candidates: list[DiscardAnalysis] = []
    for tile, count in enumerate(hand):
        if not count:
            continue
        hand[tile] -= 1
        candidates.append(DiscardAnalysis(tile, analyze_hand(hand, visible)))
        hand[tile] += 1
    return tuple(sorted(candidates, key=lambda item: (item.analysis.shanten, -item.analysis.total_effective_tiles, item.discard)))


def format_tiles(tiles: tuple[int, ...]) -> str:
    """Format tile codes for a human-facing adapter such as the CLI."""
    return " ".join(code_to_tile(tile) for tile in tiles) or "无"
