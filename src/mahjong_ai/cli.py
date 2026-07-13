"""Small command-line adapter around :mod:`mahjong_ai.analysis`."""

from __future__ import annotations

import argparse
import sys

from .analysis import analyze_discards, analyze_hand, format_tiles
from .tiles import TileError, code_to_tile, counts_from_codes, parse_tiles


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1].lower() == "game":
        from .game_cli import main as game_main

        game_main()
        return
    if len(sys.argv) > 1 and sys.argv[1].lower() == "ui":
        from .ui.main_window import main as ui_main

        ui_main()
        return
    if len(sys.argv) > 1 and sys.argv[1].lower() == "simulate":
        from .simulator.cli import simulate_main

        simulate_main(sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1].lower() == "build-dataset":
        from .simulator.cli import dataset_main

        dataset_main(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description="Analyse a simplified three-suit Mahjong hand.")
    parser.add_argument("hand", help="Hand tiles, e.g. '1w 2w 3w 5p'")
    parser.add_argument("--visible", default="", help="Known tiles outside the hand (discards/melds)")
    args = parser.parse_args()
    try:
        hand = counts_from_codes(parse_tiles(args.hand))
        visible = counts_from_codes(parse_tiles(args.visible))
        analysis = analyze_hand(hand, visible)
        discards = analyze_discards(hand, visible) if sum(hand) % 3 == 2 else ()
    except (TileError, ValueError) as error:
        parser.error(str(error))

    print(f"向听数: {analysis.shanten}")
    print(f"听牌: {format_tiles(analysis.winning_tiles)}")
    print(f"有效牌: {format_tiles(analysis.effective_tiles)}")
    if analysis.effective_tiles:
        print("有效牌剩余: " + ", ".join(f"{code_to_tile(tile)}={analysis.remaining_by_tile[tile]}" for tile in analysis.effective_tiles))
    if discards:
        print(f"推荐弃牌: {format_tiles((discards[0].discard,))}")
        print("候选弃牌:")
        for candidate in discards:
            result = candidate.analysis
            print(f"  {format_tiles((candidate.discard,))}: 向听 {result.shanten}, 有效牌 {format_tiles(result.effective_tiles)}, 剩余 {result.total_effective_tiles}")
    elif sum(hand) % 3 == 1:
        print("弃牌建议: 请在摸牌后的 14 张手牌状态下查询。")


if __name__ == "__main__":
    main()
