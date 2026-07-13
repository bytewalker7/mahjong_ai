from mahjong_ai.analysis import analyze_discards, analyze_hand
from mahjong_ai.tiles import counts_from_codes, parse_tiles, tile_to_code


def counts(text: str) -> list[int]:
    return counts_from_codes(parse_tiles(text))


def test_wait_and_remaining_count_respect_visible_tiles() -> None:
    hand = counts("1w 2w 3w 4w 5w 6w 7w 8w 9w 2s 2s 2s 5p")
    visible = counts("5p 5p")
    result = analyze_hand(hand, visible)
    assert result.shanten == 0
    assert result.winning_tiles == (tile_to_code("5p"),)
    assert result.effective_tiles == (tile_to_code("5p"),)
    assert result.remaining_by_tile[tile_to_code("5p")] == 1
    assert result.total_effective_tiles == 1


def test_discard_analysis_prefers_more_remaining_effective_tiles_on_shanten_tie() -> None:
    hand = counts("1w 2w 3w 4w 5w 6w 7w 8w 9w 2s 2s 2s 5p 5p")
    candidates = analyze_discards(hand)
    assert candidates[0].discard == tile_to_code("1w")
    assert candidates[0].analysis.shanten == 0
    assert candidates[0].analysis.total_effective_tiles == 10
