from mahjong_ai.game_cli import GameCommandProcessor


def test_game_cli_records_events_and_analyzes_own_turn() -> None:
    processor = GameCommandProcessor()
    assert "OK" in processor.execute("start self")
    result = processor.execute("hand 1w 2w 3w 4w 5w 6w 7w 8w 9w 2s 2s 2s 5p 9p")
    assert "SELF hand" in result
    analysis = processor.execute("analyze")
    assert "Recommended discard: 5p" in analysis
    processor.execute("discard self 5p")
    assert processor.state.current_player.name == "SELF"
    processor.execute("undo")
    assert processor.state.own_hand[22] == 1


def test_game_cli_records_peng_and_prevents_analysis_off_turn() -> None:
    processor = GameCommandProcessor()
    processor.execute("start self")
    processor.execute("hand 1w 2w 3w 4w 5w 6w 7w 8w 9w 2s 2s 2s 5p 9p")
    processor.execute("discard self 5p")
    result = processor.execute("peng right self 5p")
    assert "peng:5p" in result
    try:
        processor.execute("analyze")
    except ValueError as error:
        assert "SELF" in str(error)
    else:
        raise AssertionError("analysis should be rejected off turn")
