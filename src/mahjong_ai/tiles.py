"""Tile encoding and text conversion for the three numbered suits."""

from __future__ import annotations

from collections.abc import Iterable

TILE_KIND_COUNT = 27
COPIES_PER_TILE = 4
_SUIT_TO_OFFSET = {"w": 0, "s": 9, "p": 18, "万": 0, "条": 9, "筒": 18}
_OFFSET_TO_SUIT = ("w", "s", "p")


class TileError(ValueError):
    """Raised for invalid tile text or physically impossible tile counts."""


def tile_to_code(tile: str) -> int:
    """Convert a tile such as ``1w`` or ``9筒`` to its integer code."""
    normalized = tile.strip().lower()
    if len(normalized) != 2 or normalized[0] not in "123456789":
        raise TileError(f"invalid tile {tile!r}; use e.g. 1w, 9s, or 5p")
    try:
        offset = _SUIT_TO_OFFSET[normalized[1]]
    except KeyError as error:
        raise TileError(f"invalid tile suit in {tile!r}; use w, s, p, 万, 条, or 筒") from error
    return offset + int(normalized[0]) - 1


def code_to_tile(code: int) -> str:
    """Convert an integer tile code to canonical text, for example ``0 -> '1w'``."""
    if not 0 <= code < TILE_KIND_COUNT:
        raise TileError(f"tile code must be in 0..{TILE_KIND_COUNT - 1}, got {code}")
    return f"{code % 9 + 1}{_OFFSET_TO_SUIT[code // 9]}"


def counts_from_codes(codes: Iterable[int]) -> list[int]:
    """Build a validated 27-element count array from tile codes."""
    counts = [0] * TILE_KIND_COUNT
    for code in codes:
        if not 0 <= code < TILE_KIND_COUNT:
            raise TileError(f"tile code must be in 0..{TILE_KIND_COUNT - 1}, got {code}")
        counts[code] += 1
        if counts[code] > COPIES_PER_TILE:
            raise TileError(f"there cannot be more than four {code_to_tile(code)} tiles")
    return counts


def parse_tiles(text: str) -> list[int]:
    """Parse whitespace- or comma-separated tile text into tile codes."""
    tokens = text.replace(",", " ").split()
    return [tile_to_code(token) for token in tokens]


def validate_counts(counts: Iterable[int]) -> list[int]:
    """Return a checked copy of a 27-element hand count array."""
    result = list(counts)
    if len(result) != TILE_KIND_COUNT:
        raise TileError(f"counts must contain exactly {TILE_KIND_COUNT} values")
    if any(not isinstance(count, int) or not 0 <= count <= COPIES_PER_TILE for count in result):
        raise TileError("every tile count must be an integer in 0..4")
    return result
