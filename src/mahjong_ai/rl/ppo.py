"""Masked PPO Actor-Critic for the observation-only discard task."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..shanten import calculate_shanten
from .environment import DiscardRLEnvironment, RLStep
from .training import _torch, behavior_clone, evaluate, make_policy, save_policy


@dataclass(frozen=True)
class PPOConfig:
    updates: int
    episodes_per_update: int = 32
    ppo_epochs: int = 4
    minibatch_size: int = 256
    learning_rate: float = 1e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    entropy_coefficient: float = 0.01
    value_coefficient: float = 0.5
    max_gradient_norm: float = 0.5
    score_scale: float = 12.0
    shanten_potential_weight: float = 0.15


def make_value_network(feature_size: int, hidden_size: int):
    _torch_module, nn = _torch()
    return nn.Sequential(
        nn.Linear(feature_size, hidden_size), nn.LayerNorm(hidden_size), nn.ReLU(),
        nn.Linear(hidden_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 1),
    )


def state_potential(step: RLStep, weight: float) -> float:
    """Potential based only on the acting player's legal observation."""
    if step.done:
        return 0.0
    shanten = calculate_shanten(list(step.observation.own_hand), len(step.observation.own_melds))
    return -weight * float(shanten)


def _collect_episode(policy, value_network, *, seed: int, opponent_mode: str, config: PPOConfig):
    torch, _nn = _torch()
    env = DiscardRLEnvironment(opponent_mode=opponent_mode)
    step = env.reset(seed)
    trajectory: list[dict[str, object]] = []
    while not step.done:
        features = torch.tensor(step.features, dtype=torch.float32)
        mask = torch.tensor(step.legal_mask, dtype=torch.bool)
        with torch.no_grad():
            logits = policy(features).masked_fill(~mask, -1e9)
            distribution = torch.distributions.Categorical(logits=logits)
            action = distribution.sample()
            value = value_network(features).squeeze(-1)
        old_potential = state_potential(step, config.shanten_potential_weight)
        next_step = env.step(int(action.item()))
        shaped_reward = (
            float(next_step.reward) / config.score_scale
            + config.gamma * state_potential(next_step, config.shanten_potential_weight)
            - old_potential
        )
        trajectory.append({
            "features": step.features, "mask": step.legal_mask, "action": int(action.item()),
            "old_log_probability": float(distribution.log_prob(action).item()),
            "value": float(value.item()), "reward": shaped_reward, "done": next_step.done,
        })
        step = next_step

    advantage = 0.0
    next_value = 0.0
    for transition in reversed(trajectory):
        continuation = 0.0 if transition["done"] else 1.0
        delta = float(transition["reward"]) + config.gamma * next_value * continuation - float(transition["value"])
        advantage = delta + config.gamma * config.gae_lambda * continuation * advantage
        transition["advantage"] = advantage
        transition["return"] = advantage + float(transition["value"])
        next_value = float(transition["value"])
    return trajectory


def train_ppo(
    *, config: PPOConfig, seed: int, output: str | Path, report_path: str | Path,
    hidden_size: int = 128, pretrain_games: int = 0, bc_epochs: int = 5,
    opponent_mode: str = "curriculum", eval_games: int = 200,
) -> dict[str, object]:
    torch, _nn = _torch()
    torch.manual_seed(seed)
    policy = make_policy(hidden_size=hidden_size)
    value_network = make_value_network(DiscardRLEnvironment.feature_size, hidden_size)
    pretraining = behavior_clone(
        policy, games=pretrain_games, seed=seed ^ 0xBEEF, epochs=bc_epochs,
        opponent_mode=opponent_mode,
    ) if pretrain_games else None
    optimizer = torch.optim.AdamW(
        list(policy.parameters()) + list(value_network.parameters()),
        lr=config.learning_rate, weight_decay=1e-5,
    )
    generator = torch.Generator().manual_seed(seed ^ 0x50504F)
    history: list[dict[str, object]] = []
    total_decisions = 0

    for update in range(config.updates):
        rollout: list[dict[str, object]] = []
        for episode in range(config.episodes_per_update):
            rollout.extend(_collect_episode(
                policy, value_network,
                seed=seed + update * config.episodes_per_update + episode,
                opponent_mode=opponent_mode, config=config,
            ))
        if not rollout:
            continue
        total_decisions += len(rollout)
        features = torch.tensor([item["features"] for item in rollout], dtype=torch.float32)
        masks = torch.tensor([item["mask"] for item in rollout], dtype=torch.bool)
        actions = torch.tensor([item["action"] for item in rollout], dtype=torch.long)
        old_log_probabilities = torch.tensor([item["old_log_probability"] for item in rollout], dtype=torch.float32)
        returns = torch.tensor([item["return"] for item in rollout], dtype=torch.float32)
        advantages = torch.tensor([item["advantage"] for item in rollout], dtype=torch.float32)
        advantages = (advantages - advantages.mean()) / (advantages.std(unbiased=False) + 1e-8)
        losses: list[float] = []
        for _epoch in range(config.ppo_epochs):
            order = torch.randperm(len(rollout), generator=generator)
            for start in range(0, len(rollout), config.minibatch_size):
                indices = order[start:start + config.minibatch_size]
                logits = policy(features[indices]).masked_fill(~masks[indices], -1e9)
                distribution = torch.distributions.Categorical(logits=logits)
                new_log_probabilities = distribution.log_prob(actions[indices])
                ratio = (new_log_probabilities - old_log_probabilities[indices]).exp()
                unclipped = ratio * advantages[indices]
                clipped = ratio.clamp(1.0 - config.clip_range, 1.0 + config.clip_range) * advantages[indices]
                policy_loss = -torch.minimum(unclipped, clipped).mean()
                values = value_network(features[indices]).squeeze(-1)
                value_loss = torch.nn.functional.mse_loss(values, returns[indices])
                entropy = distribution.entropy().mean()
                loss = policy_loss + config.value_coefficient * value_loss - config.entropy_coefficient * entropy
                optimizer.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(list(policy.parameters()) + list(value_network.parameters()), config.max_gradient_norm)
                optimizer.step()
                losses.append(float(loss.item()))
        evaluation_seed = seed + 50_000_000 + update * eval_games
        rl = evaluate(policy, eval_games, evaluation_seed, opponent_mode=opponent_mode)
        rule = evaluate(policy, eval_games, evaluation_seed, baseline=True, opponent_mode=opponent_mode)
        history.append({
            "update": update + 1, "total_decisions": total_decisions,
            "mean_loss": sum(losses) / len(losses), "rl": rl, "rule_baseline": rule,
        })

    training_metadata = {
        "algorithm": "behavior_cloning_then_masked_PPO", "seed": seed,
        "pretrain_games": pretrain_games, "bc_epochs": bc_epochs,
        "opponent_mode": opponent_mode, "config": config.__dict__,
        "uses_bayesian_risk": False,
    }
    save_policy(output, policy, hidden_size=hidden_size, metadata=training_metadata)
    report = {"training": training_metadata, "pretraining": pretraining, "history": history, "final": history[-1] if history else {}}
    target = Path(report_path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
