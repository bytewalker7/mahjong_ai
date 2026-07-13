"""CLI entry points. They define training; they never start automatically."""

from __future__ import annotations

import argparse

from .training import evaluate, load_policy, train_reinforce


def train_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="训练只控制自己弃牌的麻将 REINFORCE 模型")
    parser.add_argument("--episodes", type=int, required=True); parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True); parser.add_argument("--report", required=True)
    parser.add_argument("--eval-games", type=int, default=200); parser.add_argument("--hidden-size", type=int, default=128)
    parser.add_argument("--pretrain-games", type=int, default=0, help="使用规则弃牌策略生成的行为克隆预训练局数")
    args = parser.parse_args(argv)
    report = train_reinforce(episodes=args.episodes, seed=args.seed, output=args.output, report_path=args.report, eval_games=args.eval_games, hidden_size=args.hidden_size, pretrain_games=args.pretrain_games)
    final = report["final"]
    print(f"训练完成：{args.output}")
    if final:
        print(f"最终固定种子评测：RL 平均分 {final['rl']['mean_score']:.3f}；规则基线平均分 {final['rule_baseline']['mean_score']:.3f}")


def evaluate_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="以固定随机对手评测 RL 与规则基线")
    parser.add_argument("--model", required=True); parser.add_argument("--games", type=int, default=1000); parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)
    policy, _metadata = load_policy(args.model)
    rl = evaluate(policy, args.games, args.seed)
    rule = evaluate(policy, args.games, args.seed, baseline=True)
    print(f"RL：平均分 {rl['mean_score']:.3f}，胜率 {rl['win_rate']:.2%}，放炮率 {rl['deal_in_rate']:.2%}")
    print(f"规则基线：平均分 {rule['mean_score']:.3f}，胜率 {rule['win_rate']:.2%}，放炮率 {rule['deal_in_rate']:.2%}")
