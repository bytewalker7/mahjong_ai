"""Optional-PyTorch REINFORCE training and fixed-seed baseline comparison."""

from __future__ import annotations

import json
from pathlib import Path

from .environment import DiscardRLEnvironment
from ..simulator.models import DiscardAction
from ..simulator.strategies import HeuristicPlayer


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as error:
        raise RuntimeError('强化学习训练需要 PyTorch。请先运行：python -m pip install -e ".[rl]"') from error
    return torch, nn


def make_policy(feature_size: int = DiscardRLEnvironment.feature_size, hidden_size: int = 128):
    torch, nn = _torch()
    return nn.Sequential(nn.Linear(feature_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 27))


def _masked_distribution(policy, features: tuple[float, ...], mask: tuple[bool, ...]):
    torch, _nn = _torch()
    logits = policy(torch.tensor(features, dtype=torch.float32))
    allowed = torch.tensor(mask, dtype=torch.bool)
    return torch.distributions.Categorical(logits=logits.masked_fill(~allowed, -1e9))


def save_policy(path: str | Path, policy, *, hidden_size: int, metadata: dict[str, object]) -> None:
    """Save plain JSON tensors; unlike pickle checkpoints, it is inspectable."""
    payload = {
        "model_type": "mahjong_rl_discard_policy", "model_version": "0.7.0",
        "feature_version": "discard_features_v1", "feature_size": DiscardRLEnvironment.feature_size,
        "hidden_size": hidden_size,
        "state_dict": {name: tensor.detach().cpu().tolist() for name, tensor in policy.state_dict().items()},
        "training_metadata": metadata,
    }
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_policy(path: str | Path):
    torch, _nn = _torch()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("model_type") != "mahjong_rl_discard_policy":
        raise ValueError("不是麻将弃牌 RL 模型")
    policy = make_policy(int(data["feature_size"]), int(data["hidden_size"]))
    state = {name: torch.tensor(values, dtype=torch.float32) for name, values in data["state_dict"].items()}
    policy.load_state_dict(state)
    policy.eval()
    return policy, data


def policy_action(policy, features: tuple[float, ...], mask: tuple[bool, ...], stochastic: bool = False) -> int:
    distribution = _masked_distribution(policy, features, mask)
    return int(distribution.sample().item()) if stochastic else int(distribution.probs.argmax().item())


def heuristic_action(step) -> int:
    player = HeuristicPlayer(seed=0)
    legal = tuple(DiscardAction(tile) for tile, allowed in enumerate(step.legal_mask) if allowed)
    return player.choose_action(step.observation, legal).tile


def behavior_clone(policy, *, games: int, seed: int, learning_rate: float = 1e-3, batch_size: int = 64) -> dict[str, float]:
    """Imitate the existing rule discard policy against random internal opponents.

    This is supervised initialization only.  It does not install a heuristic
    opponent and it never exposes another player's concealed hand to the model.
    """
    torch, _nn = _torch()
    optimizer = torch.optim.Adam(policy.parameters(), lr=learning_rate)
    teacher = HeuristicPlayer(seed=seed)
    features = []; masks = []; targets = []; losses: list[float] = []

    def update() -> None:
        if not targets:
            return
        batch_features = torch.tensor(features, dtype=torch.float32)
        batch_mask = torch.tensor(masks, dtype=torch.bool)
        labels = torch.tensor(targets, dtype=torch.long)
        logits = policy(batch_features).masked_fill(~batch_mask, -1e9)
        loss = torch.nn.functional.cross_entropy(logits, labels)
        optimizer.zero_grad(); loss.backward(); optimizer.step()
        losses.append(float(loss.item()))
        features.clear(); masks.clear(); targets.clear()

    decisions = 0
    for game in range(games):
        env = DiscardRLEnvironment()
        step = env.reset(seed + game)
        while not step.done:
            legal = tuple(DiscardAction(tile) for tile, allowed in enumerate(step.legal_mask) if allowed)
            action = teacher.choose_action(step.observation, legal)
            features.append(step.features); masks.append(step.legal_mask); targets.append(action.tile)
            decisions += 1
            if len(targets) >= batch_size:
                update()
            step = env.step(action.tile)
    update()
    return {"games": float(games), "decisions": float(decisions), "mean_cross_entropy": sum(losses) / len(losses) if losses else 0.0}


def evaluate(policy, games: int, seed: int, baseline: bool = False) -> dict[str, float]:
    """Evaluate RL or the existing rule policy against identical random-opponent seeds."""
    scores: list[int] = []; wins = 0; draws = 0; deal_ins = 0
    for offset in range(games):
        env = DiscardRLEnvironment()
        step = env.reset(seed + offset)
        while not step.done:
            tile = heuristic_action(step) if baseline else policy_action(policy, step.features, step.legal_mask)
            step = env.step(tile)
        scores.append(step.score)
        result = env.simulator.full_state.result
        wins += int(env.simulator.full_state.winner is not None and env.simulator.full_state.winner.name == "SELF")
        draws += int(result == "draw")
        deal_ins += int(result == "ron" and env.simulator.full_state.last_discard is not None and env.simulator.full_state.last_discard.player.name == "SELF")
    return {"games": float(games), "mean_score": sum(scores) / games, "win_rate": wins / games, "draw_rate": draws / games, "deal_in_rate": deal_ins / games}


def train_reinforce(*, episodes: int, seed: int, output: str | Path, report_path: str | Path, hidden_size: int = 128, learning_rate: float = 3e-4, gamma: float = 0.99, eval_games: int = 200, pretrain_games: int = 0) -> dict[str, object]:
    torch, _nn = _torch()
    torch.manual_seed(seed)
    policy = make_policy(hidden_size=hidden_size)
    optimizer = torch.optim.Adam(policy.parameters(), lr=learning_rate)
    history: list[dict[str, object]] = []
    pretraining = behavior_clone(policy, games=pretrain_games, seed=seed ^ 0xBEEF) if pretrain_games else None
    for episode in range(episodes):
        env = DiscardRLEnvironment()
        step = env.reset(seed + episode)
        log_probs = []; rewards: list[float] = []
        while not step.done:
            distribution = _masked_distribution(policy, step.features, step.legal_mask)
            action = distribution.sample()
            log_probs.append(distribution.log_prob(action))
            step = env.step(int(action.item()))
            rewards.append(step.reward)
        returns: list[float] = []; total = 0.0
        for reward in reversed(rewards):
            total = reward + gamma * total; returns.append(total)
        returns.reverse()
        values = torch.tensor(returns, dtype=torch.float32)
        if len(values) > 1:
            values = (values - values.mean()) / (values.std() + 1e-8)
        loss = -(torch.stack(log_probs) * values).mean()
        optimizer.zero_grad(); loss.backward(); optimizer.step()
        if (episode + 1) % max(1, episodes // 10) == 0 or episode + 1 == episodes:
            rl = evaluate(policy, eval_games, seed + 1_000_000 + episode * eval_games)
            rule = evaluate(policy, eval_games, seed + 1_000_000 + episode * eval_games, baseline=True)
            history.append({"episode": episode + 1, "rl": rl, "rule_baseline": rule, "mean_training_return": sum(rewards)})
    report = {"training": {"episodes": episodes, "seed": seed, "algorithm": "behavior_cloning_then_REINFORCE" if pretraining else "REINFORCE", "pretrain_games": pretrain_games, "opponents": "internal_random_only", "uses_bayesian_risk": False}, "pretraining": pretraining, "history": history, "final": history[-1] if history else {}}
    save_policy(output, policy, hidden_size=hidden_size, metadata=report["training"])
    target = Path(report_path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
