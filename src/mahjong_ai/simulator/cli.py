"""Batch command-line entry points for simulation and dataset extraction."""

from __future__ import annotations

import argparse
import time

from ..dataset import extract_samples, save_samples
from ..simulator.logging import load_full_log, save_full_log
from .runner import simulate_game


def simulate_main(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser(description="生成全知麻将模拟牌谱")
    parser.add_argument("--games", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(arguments)
    started = time.perf_counter()
    logs = []
    failures = 0
    for index in range(args.games):
        try:
            logs.append(simulate_game(args.seed + index, game_id=f"game-{args.seed + index}"))
        except Exception:
            failures += 1
    save_full_log(logs, args.output)
    elapsed = time.perf_counter() - started
    print(f"已生成 {len(logs)} 局，异常局 {failures}，耗时 {elapsed:.2f} 秒，输出：{args.output}")


def dataset_main(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser(description="从全知牌谱构建贝叶斯样本")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(arguments)
    started = time.perf_counter()
    logs = load_full_log(args.input)
    samples = [sample for log in logs for sample in extract_samples(log)]
    count = save_samples(samples, args.output)
    elapsed = time.perf_counter() - started
    print(f"已处理 {len(logs)} 局，生成 {count} 条样本，耗时 {elapsed:.2f} 秒，输出：{args.output}")
