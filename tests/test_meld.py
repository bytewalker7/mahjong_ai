import pytest

from mahjong_ai.analysis import analyze_discards, analyze_hand
from mahjong_ai.meld import Meld, MeldType
from mahjong_ai.tiles import counts_from_codes, parse_tiles, tile_to_code


def counts(text: str) -> list[int]:
    return counts_from_codes(parse_tiles(text))


def test_each_meld_type_occupies_one_fixed_meld_slot() -> None:
    hand = counts("1w 2w 3w 4w 5w 6w 7w 8w 9w 5p")
    for meld_type in MeldType:
        from_player = 1 if meld_type in (MeldType.PENG, MeldType.EXPOSED_GANG) else None
        meld = Meld(meld_type, tile_to_code("2s"), from_player)
        assert analyze_hand(hand, melds=(meld,)).shanten == 0


def test_concrete_meld_reduces_theoretical_remaining_tiles() -> None:
    meld = Meld(MeldType.PENG, tile_to_code("2s"), from_player=1)
    hand = counts("1w 2w 3w 4w 5w 6w 7w 8w 9w 5p")
    result = analyze_hand(hand, melds=(meld,))
    assert result.shanten == 0
    assert result.winning_tiles == (tile_to_code("5p"),)
    assert result.remaining_by_tile[tile_to_code("2s")] == 1


def test_open_hand_discard_analysis_uses_fixed_melds() -> None:
    meld = Meld(MeldType.PENG, tile_to_code("5p"), from_player=1)
    hand = counts("1w 2w 3w 4w 5w 6w 7w 8w 2s 2s 9p")
    candidates = analyze_discards(hand, melds=(meld,))
    assert candidates[0].discard == tile_to_code("9p")
    assert candidates[0].analysis.shanten == 0


def test_meld_validation_rejects_invalid_call_source() -> None:
    with pytest.raises(ValueError):
        Meld(MeldType.PENG, tile_to_code("1w"))
