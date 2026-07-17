"""RL command-line entry points; training never starts implicitly."""

from __future__ import annotations

import argparse

from .training import evaluate, load_policy, train_reinforce
from .ppo import PPOConfig, train_ppo


OPPONENT_CHOICES = ("random", "noisy", "heuristic", "curriculum")


def train_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="训练只控制自己弃牌的麻将策略模型")
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--eval-games", type=int, default=200)
    parser.add_argument("--hidden-size", type=int, default=128)
    parser.add_argument("--pretrain-games", type=int, default=0, help="规则教师生成的行为克隆示范局数")
    parser.add_argument("--bc-epochs", type=int, default=5, help="行为克隆重复训练轮数")
    parser.add_argument("--opponents", choices=OPPONENT_CHOICES, default="curriculum")
    args = parser.parse_args(argv)
    report = train_reinforce(
        episodes=args.episodes, seed=args.seed, output=args.output, report_path=args.report,
        eval_games=args.eval_games, hidden_size=args.hidden_size,
        pretrain_games=args.pretrain_games, bc_epochs=args.bc_epochs,
        opponent_mode=args.opponents,
    )
    final = report["final"]
    print(f"训练完成：{args.output}")
    if final:
        print(f"最终固定种子评测：RL 平均分 {final['rl']['mean_score']:.3f}；规则基线平均分 {final['rule_baseline']['mean_score']:.3f}")


def evaluate_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="以固定对手和种子评测 RL 与规则基线")
    parser.add_argument("--model", required=True)
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--opponents", choices=OPPONENT_CHOICES, default="random")
    args = parser.parse_args(argv)
    policy, _metadata = load_policy(args.model)
    rl = evaluate(policy, args.games, args.seed, opponent_mode=args.opponents)
    rule = evaluate(policy, args.games, args.seed, baseline=True, opponent_mode=args.opponents)
    print(f"RL：平均分 {rl['mean_score']:.3f}，胜率 {rl['win_rate']:.2%}，非流局胜率 {rl['conditional_win_rate']:.2%}，流局率 {rl['draw_rate']:.2%}，放炮率 {rl['deal_in_rate']:.2%}")
    print(f"规则基线：平均分 {rule['mean_score']:.3f}，胜率 {rule['win_rate']:.2%}，非流局胜率 {rule['conditional_win_rate']:.2%}，流局率 {rule['draw_rate']:.2%}，放炮率 {rule['deal_in_rate']:.2%}")


def ppo_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="训练带合法动作遮罩的 PPO Actor-Critic 麻将弃牌模型")
    parser.add_argument("--updates", type=int, required=True)
    parser.add_argument("--episodes-per-update", type=int, default=32)
    parser.add_argument("--ppo-epochs", type=int, default=4)
    parser.add_argument("--pretrain-games", type=int, default=0)
    parser.add_argument("--bc-epochs", type=int, default=5)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--hidden-size", type=int, default=128)
    parser.add_argument("--opponents", choices=OPPONENT_CHOICES, default="curriculum")
    parser.add_argument("--eval-games", type=int, default=200)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    config = PPOConfig(
        updates=args.updates, episodes_per_update=args.episodes_per_update,
        ppo_epochs=args.ppo_epochs,
    )
    report = train_ppo(
        config=config, seed=args.seed, output=args.output, report_path=args.report,
        hidden_size=args.hidden_size, pretrain_games=args.pretrain_games,
        bc_epochs=args.bc_epochs, opponent_mode=args.opponents,
        eval_games=args.eval_games,
    )
    final = report["final"]
    print(f"PPO 训练完成：{args.output}")
    if final:
        print(f"最终固定种子评测：PPO 平均分 {final['rl']['mean_score']:.3f}；规则基线平均分 {final['rule_baseline']['mean_score']:.3f}")
