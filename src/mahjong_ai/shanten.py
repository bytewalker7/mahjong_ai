"""Standard-hand shanten calculation for the three numbered suits."""

from __future__ import annotations

from .tiles import validate_counts


def calculate_shanten(counts: list[int]) -> int:
    """Return standard shanten (``-1`` means a complete winning hand).

    Only the regular four-meld-and-a-pair shape is considered.  The recursive
    search allocates tiles to complete melds, incomplete melds (taatsu), and a
    possible pair, then applies the usual ``8 - 2*m - t - pair`` formula.
    """
    hand = validate_counts(counts)
    best = 8

    def visit(index: int, melds: int, taatsu: int, has_pair: int) -> None:
        nonlocal best
        while index < 27 and hand[index] == 0:
            index += 1
        if index == 27:
            usable_taatsu = min(taatsu, 4 - melds)
            best = min(best, 8 - 2 * melds - usable_taatsu - has_pair)
            return

        # Ignore one copy.  This is necessary because a tile need not form a
        # useful block in the optimal decomposition.
        hand[index] -= 1
        visit(index, melds, taatsu, has_pair)
        hand[index] += 1

        if melds < 4 and hand[index] >= 3:
            hand[index] -= 3
            visit(index, melds + 1, taatsu, has_pair)
            hand[index] += 3

        rank = index % 9
        if melds < 4 and rank <= 6 and hand[index + 1] and hand[index + 2]:
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

        if taatsu < 4 and hand[index] >= 2:
            hand[index] -= 2
            visit(index, melds, taatsu + 1, has_pair)
            hand[index] += 2

        if taatsu < 4 and rank <= 7 and hand[index + 1]:
            hand[index] -= 1
            hand[index + 1] -= 1
            visit(index, melds, taatsu + 1, has_pair)
            hand[index] += 1
            hand[index + 1] += 1

        if taatsu < 4 and rank <= 6 and hand[index + 2]:
            hand[index] -= 1
            hand[index + 2] -= 1
            visit(index, melds, taatsu + 1, has_pair)
            hand[index] += 1
            hand[index + 2] += 1

    visit(0, 0, 0, 0)
    return best
