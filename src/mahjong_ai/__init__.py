"""Algorithms for analysing simplified three-suit Mahjong hands."""

from .analysis import HandAnalysis, DiscardAnalysis, analyze_hand, analyze_discards
from .tiles import TileError, parse_tiles, tile_to_code, code_to_tile

__all__ = [
    "DiscardAnalysis",
    "HandAnalysis",
    "TileError",
    "analyze_discards",
    "analyze_hand",
    "code_to_tile",
    "parse_tiles",
    "tile_to_code",
]
