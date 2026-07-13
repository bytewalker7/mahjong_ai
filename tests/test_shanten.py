from mahjong_ai.shanten import calculate_shanten
from mahjong_ai.tiles import counts_from_codes, parse_tiles


def counts(text: str) -> list[int]:
    return counts_from_codes(parse_tiles(text))


def test_complete_regular_hand_is_minus_one_shanten() -> None:
    hand = counts("1w 2w 3w 4w 5w 6w 7w 8w 9w 2s 2s 2s 5p 5p")
    assert calculate_shanten(hand) == -1


def test_tenpai_hand_is_zero_shanten() -> None:
    hand = counts("1w 2w 3w 4w 5w 6w 7w 8w 9w 2s 2s 2s 5p")
    assert calculate_shanten(hand) == 0
