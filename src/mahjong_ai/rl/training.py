"""Observation-only discard-policy training and reproducible evaluation."""

from __future__ import annotations

import json
import math
from pathlib import Path

from ..shanten import calculate_shanten
from ..simulator.models import DiscardAction
from ..simulator.strategies import HeuristicPlayer
from ..state.models import PlayerPosition
from .environment import DiscardRLEnvironment


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as error:
        raise RuntimeError('强化学习训练需要 PyTorch。请先运行：python -m pip install -e ".[rl]"') from error
    return torch, nn


def make_policy(feature_size: int = DiscardRLEnvironment.feature_size, hidden_size: int = 128, architecture: str = "tile_scorer_v1"):
    torch, nn = _torch()
    if architecture == "legacy_mlp_v1":
        return nn.Sequential(nn.Linear(feature_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 27))
    if architecture == "tile_scorer_v1":
        if feature_size != DiscardRLEnvironment.feature_size:
            raise ValueError("tile scorer requires discard_features_v2")

        class TileScorer(nn.Module):
            """Score each tile with shared weights plus public global context."""

            def __init__(self) -> None:
                super().__init__()
                context_size = max(32, hidden_size // 2)
                self.global_encoder = nn.Sequential(
                    nn.Linear(feature_size, hidden_size), nn.LayerNorm(hidden_size), nn.ReLU(),
                    nn.Linear(hidden_size, context_size), nn.ReLU(),
                )
                self.local_encoder = nn.Sequential(nn.Linear(20, context_size), nn.ReLU())
                self.scorer = nn.Sequential(nn.Linear(context_size * 2, context_size), nn.ReLU(), nn.Linear(context_size, 1))
                identity = []
                for tile in range(27):
                    suit = tile // 9
                    rank = tile % 9
                    identity.append([
                        float(suit == 0), float(suit == 1), float(suit == 2),
                        rank / 8.0, float(rank in (0, 8)),
                    ])
                self.register_buffer("tile_identity", torch.tensor(identity, dtype=torch.float32))

            def forward(self, features):
                squeeze = features.ndim == 1
                if squeeze:
                    features = features.unsqueeze(0)
                batch = features.shape[0]
                own = features[:, 0:27].unsqueeze(-1)
                visible = features[:, 27:54].unsqueeze(-1)
                discards = features[:, 58:166].reshape(batch, 4, 27).permute(0, 2, 1)
                recent = features[:, 166:278].reshape(batch, 4, 28)[:, :, :27].permute(0, 2, 1)
                melds = features[:, 278:386].reshape(batch, 4, 27).permute(0, 2, 1)
                last = features[:, 406:433].unsqueeze(-1)
                identity = self.tile_identity.unsqueeze(0).expand(batch, -1, -1)
                local = torch.cat((own, visible, discards, recent, melds, last, identity), dim=-1)
                local_context = self.local_encoder(local)
                global_context = self.global_encoder(features).unsqueeze(1).expand(-1, 27, -1)
                logits = self.scorer(torch.cat((local_context, global_context), dim=-1)).squeeze(-1)
                return logits.squeeze(0) if squeeze else logits

        return TileScorer()
    if architecture != "mlp_v2":
        raise ValueError(f"unknown policy architecture: {architecture}")
    return nn.Sequential(
        nn.Linear(feature_size, hidden_size), nn.LayerNorm(hidden_size), nn.ReLU(),
        nn.Linear(hidden_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 27),
    )


def _masked_distribution(policy, features: tuple[float, ...], mask: tuple[bool, ...]):
    torch, _nn = _torch()
    logits = policy(torch.tensor(features, dtype=torch.float32))
    allowed = torch.tensor(mask, dtype=torch.bool)
    return torch.distributions.Categorical(logits=logits.masked_fill(~allowed, -1e9))


def save_policy(path: str | Path, policy, *, hidden_size: int, metadata: dict[str, object], architecture: str = "tile_scorer_v1") -> None:
    """Save inspectable JSON tensors instead of an unsafe pickle checkpoint."""
    payload = {
        "model_type": "mahjong_rl_discard_policy", "model_version": "0.8.0",
        "feature_version": DiscardRLEnvironment.feature_version,
        "feature_size": DiscardRLEnvironment.feature_size,
        "hidden_size": hidden_size, "architecture": architecture,
        "state_dict": {name: tensor.detach().cpu().tolist() for name, tensor in policy.state_dict().items()},
        "training_metadata": metadata,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_policy(path: str | Path):
    torch, _nn = _torch()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("model_type") != "mahjong_rl_discard_policy":
        raise ValueError("不是麻将弃牌 RL 模型")
    architecture = str(data.get("architecture", "legacy_mlp_v1"))
    policy = make_policy(int(data["feature_size"]), int(data["hidden_size"]), architecture)
    state = {name: torch.tensor(values, dtype=torch.float32) for name, values in data["state_dict"].items()}
    policy.load_state_dict(state)
    policy.eval()
    return policy, data


def policy_action(policy, features: tuple[float, ...], mask: tuple[bool, ...], stochastic: bool = False) -> int:
    distribution = _masked_distribution(policy, features, mask)
    return int(distribution.sample().item()) if stochastic else int(distribution.probs.argmax().item())


def _policy_features(policy, step) -> tuple[float, ...]:
    expected = next(parameter for parameter in policy.parameters() if parameter.ndim == 2).shape[1]
    if expected == len(step.features):
        return step.features
    if expected == 60:
        return DiscardRLEnvironment.encode_v1(step.observation)
    raise ValueError(f"policy expects {expected} features, environment produced {len(step.features)}")


def heuristic_action(step) -> int:
    player = HeuristicPlayer(seed=0)
    legal = tuple(DiscardAction(tile) for tile, allowed in enumerate(step.legal_mask) if allowed)
    return player.choose_action(step.observation, legal).tile


def heuristic_target(step, teacher: HeuristicPlayer | None = None) -> tuple[float, ...]:
    """Return a soft label over every equally good heuristic discard."""
    teacher = teacher or HeuristicPlayer(seed=0)
    legal = {tile for tile, allowed in enumerate(step.legal_mask) if allowed}
    ranked = [candidate for candidate in teacher._rank_discards(step.observation) if candidate[0] in legal]
    if not ranked:
        raise ValueError("teacher received no legal discard")
    best_metrics = ranked[0][1:]
    best_tiles = [candidate[0] for candidate in ranked if candidate[1:] == best_metrics]
    probability = 1.0 / len(best_tiles)
    return tuple(probability if tile in best_tiles else 0.0 for tile in range(27))


def _soft_cross_entropy(logits, targets):
    torch, _nn = _torch()
    return -(targets * torch.nn.functional.log_softmax(logits, dim=-1)).sum(dim=-1).mean()


def _collect_teacher_data(*, games: int, seed: int, opponent_mode: str):
    """Collect one deterministic demonstration pass into compact tensors."""
    torch, _nn = _torch()
    teacher = HeuristicPlayer(seed=seed)
    feature_chunks = []
    mask_chunks = []
    target_chunks = []
    features: list[tuple[float, ...]] = []
    masks: list[tuple[bool, ...]] = []
    targets_batch: list[tuple[float, ...]] = []

    def flush() -> None:
        if not targets_batch:
            return
        feature_chunks.append(torch.tensor(features, dtype=torch.float32))
        mask_chunks.append(torch.tensor(masks, dtype=torch.bool))
        target_chunks.append(torch.tensor(targets_batch, dtype=torch.float32))
        features.clear(); masks.clear(); targets_batch.clear()

    for game in range(games):
        env = DiscardRLEnvironment(opponent_mode=opponent_mode)
        step = env.reset(seed + game)
        while not step.done:
            targets = heuristic_target(step, teacher)
            features.append(step.features)
            masks.append(step.legal_mask)
            targets_batch.append(targets)
            if len(targets_batch) >= 2048:
                flush()
            step = env.step(next(tile for tile, probability in enumerate(targets) if probability > 0.0))
    flush()
    if not feature_chunks:
        return (
            torch.empty((0, DiscardRLEnvironment.feature_size), dtype=torch.float32),
            torch.empty((0, 27), dtype=torch.bool),
            torch.empty((0, 27), dtype=torch.float32),
        )
    return torch.cat(feature_chunks), torch.cat(mask_chunks), torch.cat(target_chunks)


def _bc_metrics(policy, features, masks, targets, *, batch_size: int = 1024) -> dict[str, float]:
    torch, _nn = _torch()
    decisions = int(features.shape[0])
    if decisions == 0:
        return {"decisions": 0.0, "cross_entropy": 0.0, "tie_aware_accuracy": 0.0}
    loss_sum = 0.0
    tie_hits = 0
    policy.eval()
    with torch.no_grad():
        for start in range(0, decisions, batch_size):
            end = min(start + batch_size, decisions)
            logits = policy(features[start:end]).masked_fill(~masks[start:end], -1e9)
            losses = -(targets[start:end] * torch.nn.functional.log_softmax(logits, dim=-1)).sum(dim=-1)
            loss_sum += float(losses.sum().item())
            predicted = logits.argmax(dim=-1)
            tie_hits += int((targets[start:end].gather(1, predicted.unsqueeze(1)).squeeze(1) > 0.0).sum().item())
    policy.train()
    return {
        "decisions": float(decisions), "cross_entropy": loss_sum / decisions,
        "tie_aware_accuracy": tie_hits / decisions,
    }


def behavior_clone(
    policy, *, games: int, seed: int, learning_rate: float = 1e-3,
    batch_size: int = 256, epochs: int = 5, validation_games: int | None = None,
    opponent_mode: str = "curriculum",
) -> dict[str, object]:
    """Imitate tied-optimal heuristic discards for deterministic epochs."""
    torch, _nn = _torch()
    optimizer = torch.optim.AdamW(policy.parameters(), lr=learning_rate, weight_decay=1e-5)
    torch_generator = torch.Generator().manual_seed(seed ^ 0xBC08)
    epoch_reports: list[dict[str, float]] = []
    validation_games = validation_games if validation_games is not None else min(500, max(20, games // 10))
    train_features, train_masks, train_targets = _collect_teacher_data(games=games, seed=seed, opponent_mode=opponent_mode)
    validation_features, validation_masks, validation_targets = _collect_teacher_data(
        games=validation_games, seed=seed + 10_000_000, opponent_mode=opponent_mode,
    )
    decisions = int(train_features.shape[0])
    for epoch in range(epochs):
        losses: list[float] = []
        policy.train()
        order = torch.randperm(decisions, generator=torch_generator)
        for start in range(0, decisions, batch_size):
            indices = order[start:start + batch_size]
            logits = policy(train_features[indices]).masked_fill(~train_masks[indices], -1e9)
            loss = _soft_cross_entropy(logits, train_targets[indices])
            optimizer.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.item()))
        validation = _bc_metrics(policy, validation_features, validation_masks, validation_targets)
        epoch_reports.append({
            "epoch": float(epoch + 1), "decisions": float(decisions),
            "mean_training_cross_entropy": sum(losses) / len(losses) if losses else 0.0,
            "validation_cross_entropy": validation["cross_entropy"],
            "validation_tie_aware_accuracy": validation["tie_aware_accuracy"],
        })
    return {
        "games": float(games), "epochs": float(epochs), "opponent_mode": opponent_mode,
        "validation_games": float(validation_games), "history": epoch_reports,
        "final": epoch_reports[-1] if epoch_reports else {},
    }


def evaluate(policy, games: int, seed: int, baseline: bool = False, opponent_mode: str = "random") -> dict[str, float]:
    """Evaluate policy and rule baseline with identical seeds and opponents."""
    scores: list[int] = []
    wins = draws = deal_ins = draw_tenpai = decisions = draw_shanten_sum = 0
    for offset in range(games):
        env = DiscardRLEnvironment(opponent_mode=opponent_mode)
        step = env.reset(seed + offset)
        while not step.done:
            tile = heuristic_action(step) if baseline else policy_action(policy, _policy_features(policy, step), step.legal_mask)
            decisions += 1
            step = env.step(tile)
        scores.append(step.score)
        state = env.simulator.full_state
        wins += int(state.winner is PlayerPosition.SELF)
        is_draw = state.result == "draw"
        draws += int(is_draw)
        deal_ins += int(state.result == "ron" and state.last_discard is not None and state.last_discard.player is PlayerPosition.SELF)
        if is_draw:
            shanten = calculate_shanten(state.players[PlayerPosition.SELF].hand, len(state.players[PlayerPosition.SELF].melds))
            draw_tenpai += int(shanten == 0)
            draw_shanten_sum += shanten
    decisive = games - draws
    mean_score = sum(scores) / games
    variance = sum((score - mean_score) ** 2 for score in scores) / games
    return {
        "games": float(games), "mean_score": mean_score, "score_stddev": math.sqrt(variance),
        "win_rate": wins / games, "conditional_win_rate": wins / decisive if decisive else 0.0,
        "draw_rate": draws / games, "deal_in_rate": deal_ins / games,
        "tenpai_at_draw_rate": draw_tenpai / draws if draws else 0.0,
        "mean_shanten_at_draw": draw_shanten_sum / draws if draws else 0.0,
        "mean_decisions": decisions / games,
    }


def train_reinforce(
    *, episodes: int, seed: int, output: str | Path, report_path: str | Path,
    hidden_size: int = 128, learning_rate: float = 3e-4, gamma: float = 0.99,
    eval_games: int = 200, pretrain_games: int = 0, bc_epochs: int = 5,
    opponent_mode: str = "curriculum",
) -> dict[str, object]:
    """Legacy policy-gradient entry point retained while PPO is introduced."""
    torch, _nn = _torch()
    torch.manual_seed(seed)
    policy = make_policy(hidden_size=hidden_size)
    optimizer = torch.optim.Adam(policy.parameters(), lr=learning_rate)
    history: list[dict[str, object]] = []
    pretraining = behavior_clone(policy, games=pretrain_games, seed=seed ^ 0xBEEF, epochs=bc_epochs, opponent_mode=opponent_mode) if pretrain_games else None
    for episode in range(episodes):
        env = DiscardRLEnvironment(opponent_mode=opponent_mode)
        step = env.reset(seed + episode)
        log_probs = []
        rewards: list[float] = []
        while not step.done:
            distribution = _masked_distribution(policy, step.features, step.legal_mask)
            action = distribution.sample()
            log_probs.append(distribution.log_prob(action))
            step = env.step(int(action.item()))
            rewards.append(step.reward)
        returns: list[float] = []
        total = 0.0
        for reward in reversed(rewards):
            total = reward + gamma * total
            returns.append(total)
        returns.reverse()
        values = torch.tensor(returns, dtype=torch.float32)
        if len(values) > 1:
            values = (values - values.mean()) / (values.std() + 1e-8)
        loss = -(torch.stack(log_probs) * values).mean()
        optimizer.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
        optimizer.step()
        if (episode + 1) % max(1, episodes // 10) == 0 or episode + 1 == episodes:
            evaluation_seed = seed + 1_000_000 + episode * eval_games
            rl = evaluate(policy, eval_games, evaluation_seed, opponent_mode=opponent_mode)
            rule = evaluate(policy, eval_games, evaluation_seed, baseline=True, opponent_mode=opponent_mode)
            history.append({"episode": episode + 1, "rl": rl, "rule_baseline": rule, "mean_training_return": sum(rewards)})
    training_metadata = {
        "episodes": episodes, "seed": seed,
        "algorithm": "behavior_cloning_then_REINFORCE" if pretraining else "REINFORCE",
        "pretrain_games": pretrain_games, "bc_epochs": bc_epochs,
        "opponent_mode": opponent_mode, "uses_bayesian_risk": False,
    }
    report = {"training": training_metadata, "pretraining": pretraining, "history": history, "final": history[-1] if history else {}}
    save_policy(output, policy, hidden_size=hidden_size, metadata=training_metadata)
    target = Path(report_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
