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


def test_zero_fixed_melds_is_identical_to_v01_call() -> None:
    hand = counts("1w 2w 3w 4w 6w 7w 2s 3s 5s 5s 6p 7p 8p")
    assert calculate_shanten(hand, fixed_melds=0) == calculate_shanten(hand)


def test_one_fixed_meld_needs_only_three_more_melds_and_a_pair() -> None:
    hand = counts("1w 2w 3w 4w 5w 6w 7w 8w 9w 5p 5p")
    assert calculate_shanten(hand, fixed_melds=1) == -1


def test_two_fixed_melds_need_only_two_more_melds_and_a_pair() -> None:
    hand = counts("1w 2w 3w 4w 5w 6w 5p 5p")
    assert calculate_shanten(hand, fixed_melds=2) == -1
