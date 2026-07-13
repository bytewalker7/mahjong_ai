import pytest

from mahjong_ai.tiles import TileError, code_to_tile, counts_from_codes, parse_tiles, tile_to_code


def test_tile_code_round_trip() -> None:
    assert tile_to_code("1w") == 0
    assert tile_to_code("9s") == 17
    assert tile_to_code("1p") == 18
    assert tile_to_code("5筒") == 22
    assert code_to_tile(22) == "5p"
    assert parse_tiles("1w, 2s 3p") == [0, 10, 20]


def test_rejects_invalid_or_five_copies() -> None:
    with pytest.raises(TileError):
        tile_to_code("10w")
    with pytest.raises(TileError):
        counts_from_codes([0] * 5)
