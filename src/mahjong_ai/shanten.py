"""Standard-hand shanten calculation for the three numbered suits."""

from __future__ import annotations

from functools import lru_cache

from .meld import validate_fixed_melds
from .tiles import validate_counts


def calculate_shanten(counts: list[int], fixed_melds: int = 0) -> int:
    """Return standard shanten (``-1`` means a complete winning hand).

    Only the regular four-meld-and-a-pair shape is considered. ``fixed_melds``
    represents completed pengs or gangs outside the concealed hand; each uses
    one meld slot, including a four-tile gang. The recursive search allocates
    the remaining concealed tiles to melds, incomplete melds (taatsu), and a
    possible pair.
    """
    hand = validate_counts(counts)
    fixed_melds = validate_fixed_melds(fixed_melds)
    return _calculate_shanten_by_suit(tuple(hand), fixed_melds)


@lru_cache(maxsize=250_000)
def _suit_options(counts: tuple[int, ...]) -> tuple[tuple[int, int, int], ...]:
    """Return nondominated ``(melds, taatsu, has_pair)`` decompositions.

    Numbered suits never form blocks across suit boundaries.  Decomposing each
    nine-tile suit separately turns the former 27-tile recursive hot path into
    three small cached lookups followed by a compact Cartesian product.
    """
    tiles = list(counts)
    results: set[tuple[int, int, int]] = set()

    def visit(index: int, melds: int, taatsu: int, has_pair: int) -> None:
        while index < 9 and tiles[index] == 0:
            index += 1
        if index == 9:
            results.add((melds, taatsu, has_pair))
            return

        tiles[index] -= 1
        visit(index, melds, taatsu, has_pair)
        tiles[index] += 1

        if tiles[index] >= 3:
            tiles[index] -= 3
            visit(index, melds + 1, taatsu, has_pair)
            tiles[index] += 3

        if index <= 6 and tiles[index + 1] and tiles[index + 2]:
            tiles[index] -= 1; tiles[index + 1] -= 1; tiles[index + 2] -= 1
            visit(index, melds + 1, taatsu, has_pair)
            tiles[index] += 1; tiles[index + 1] += 1; tiles[index + 2] += 1

        if tiles[index] >= 2:
            tiles[index] -= 2
            visit(index, melds, taatsu + 1, has_pair)
            if not has_pair:
                visit(index, melds, taatsu, 1)
            tiles[index] += 2

        if index <= 7 and tiles[index + 1]:
            tiles[index] -= 1; tiles[index + 1] -= 1
            visit(index, melds, taatsu + 1, has_pair)
            tiles[index] += 1; tiles[index + 1] += 1

        if index <= 6 and tiles[index + 2]:
            tiles[index] -= 1; tiles[index + 2] -= 1
            visit(index, melds, taatsu + 1, has_pair)
            tiles[index] += 1; tiles[index + 2] += 1

    visit(0, 0, 0, 0)
    # A decomposition is dominated when another has at least as many complete
    # and incomplete groups with the same head choice.
    useful = {
        option for option in results
        if not any(
            other[2] == option[2]
            and other[0] >= option[0]
            and other[1] >= option[1]
            and other != option
            for other in results
        )
    }
    return tuple(sorted(useful))


@lru_cache(maxsize=250_000)
def _calculate_shanten_by_suit(counts: tuple[int, ...], fixed_melds: int) -> int:
    suits = (_suit_options(counts[0:9]), _suit_options(counts[9:18]), _suit_options(counts[18:27]))
    best = 8
    for first in suits[0]:
        for second in suits[1]:
            pair12 = first[2] + second[2]
            if pair12 > 1:
                continue
            for third in suits[2]:
                pairs = pair12 + third[2]
                if pairs > 1:
                    continue
                melds = fixed_melds + first[0] + second[0] + third[0]
                if melds > 4:
                    continue
                taatsu = min(first[1] + second[1] + third[1], 4 - melds)
                best = min(best, 8 - 2 * melds - taatsu - pairs)
    return best


@lru_cache(maxsize=250_000)
def _calculate_shanten_cached(counts: tuple[int, ...], fixed_melds: int) -> int:
    """Memoized implementation for repeated candidate-discard evaluation."""
    hand = list(counts)
    best = 8

    def visit(index: int, melds: int, taatsu: int, has_pair: int) -> None:
        nonlocal best
        while index < 27 and hand[index] == 0:
            index += 1
        if index == 27:
            total_melds = fixed_melds + melds
            usable_taatsu = min(taatsu, 4 - total_melds)
            best = min(best, 8 - 2 * total_melds - usable_taatsu - has_pair)
            return

        # Ignore one copy.  This is necessary because a tile need not form a
        # useful block in the optimal decomposition.
        hand[index] -= 1
        visit(index, melds, taatsu, has_pair)
        hand[index] += 1

        if fixed_melds + melds < 4 and hand[index] >= 3:
            hand[index] -= 3
            visit(index, melds + 1, taatsu, has_pair)
            hand[index] += 3

        rank = index % 9
        if fixed_melds + melds < 4 and rank <= 6 and hand[index + 1] and hand[index + 2]:
            hand[index] -= 1
            hand[index + 1] -= 1
            hand[index + 2] -= 1
            visit(index, melds + 1, taatsu, has_pair)
            hand[index] += 1
            hand[index + 1] += 1
            hand[index + 2] += 1

        if not has_pair and hand[index] >= 2:
            hand[index] -= 2
            visit(index, melds, taatsu, 1)
            hand[index] += 2

        if taatsu < 4 - fixed_melds and hand[index] >= 2:
            hand[index] -= 2
            visit(index, melds, taatsu + 1, has_pair)
            hand[index] += 2

        if taatsu < 4 - fixed_melds and rank <= 7 and hand[index + 1]:
            hand[index] -= 1
            hand[index + 1] -= 1
            visit(index, melds, taatsu + 1, has_pair)
            hand[index] += 1
            hand[index + 1] += 1

        if taatsu < 4 - fixed_melds and rank <= 6 and hand[index + 2]:
            hand[index] -= 1
            hand[index + 2] -= 1
            visit(index, melds, taatsu + 1, has_pair)
            hand[index] += 1
            hand[index + 2] += 1

    visit(0, 0, 0, 0)
    return best
