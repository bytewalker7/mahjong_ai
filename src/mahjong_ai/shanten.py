"""Standard-hand shanten calculation for the three numbered suits."""

from __future__ import annotations

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
