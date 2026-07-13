from mahjong_ai.dataset import load_samples
from mahjong_ai.simulator.cli import dataset_main, simulate_main
from mahjong_ai.simulator.logging import load_full_log


def test_simulate_and_dataset_cli(tmp_path) -> None:
    games = tmp_path / "full.jsonl"
    samples = tmp_path / "samples.jsonl"
    simulate_main(["--games", "2", "--seed", "41", "--output", str(games)])
    assert len(load_full_log(games)) == 2
    dataset_main(["--input", str(games), "--output", str(samples)])
    assert load_samples(samples)
