"""Explainable Naive-Bayes models for public Mahjong opponent risk.

The three-opponent aggregate uses a *conditional-independence approximation*;
opponents' tenpai states and waits are not actually independent.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
from typing import Iterable, Mapping

from .features import public_context_from_observation, public_context_from_sample, tenpai_features, wait_features
from ..dataset.schema import BayesianSample
from ..simulator.models import Observation, Phase
from ..state.models import PlayerPosition
from ..tiles import TILE_KIND_COUNT


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sample_dict(sample: BayesianSample | Mapping[str, object]) -> dict[str, object]:
    return sample.to_dict() if isinstance(sample, BayesianSample) else dict(sample)


def is_valid_wait_training_sample(sample: BayesianSample | Mapping[str, object]) -> bool:
    """Whether a sample is a normal, externally-discardable tenpai wait state."""
    row = _sample_dict(sample)
    mask = row.get("target_wait_mask")
    danger = row.get("target_danger_mask")
    public = row.get("public_input")
    if not bool(row.get("target_is_tenpai")) or not isinstance(mask, (tuple, list)) or len(mask) != TILE_KIND_COUNT:
        return False
    if not isinstance(danger, (tuple, list)) or len(danger) != TILE_KIND_COUNT or not any(bool(x) for x in danger):
        return False
    if not isinstance(public, Mapping) or int(public.get("target_concealed_tile_count", -1)) % 3 != 1:
        return False
    if str(public.get("sample_stage", "")) == "finished":
        return False
    return all(isinstance(value, (bool, int)) and int(value) in (0, 1) for value in mask)


def expand_wait_samples(sample: BayesianSample | Mapping[str, object]) -> tuple[tuple[int, int], ...]:
    """Expand one valid tenpai state into its 27 candidate wait labels."""
    if not is_valid_wait_training_sample(sample):
        return ()
    row = _sample_dict(sample)
    mask = row["target_wait_mask"]
    return tuple((tile, int(bool(mask[tile]))) for tile in range(TILE_KIND_COUNT))


@dataclass(frozen=True)
class CategoricalNaiveBayes:
    class_counts: dict[str, int]
    feature_counts: dict[str, dict[str, dict[str, int]]]
    feature_values: dict[str, tuple[str, ...]]
    alpha: float = 1.0

    @classmethod
    def fit(cls, rows: Iterable[tuple[Mapping[str, str], int]], alpha: float = 1.0) -> "CategoricalNaiveBayes":
        classes: Counter[str] = Counter()
        counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
        values: dict[str, set[str]] = defaultdict(set)
        for features, label in rows:
            key = str(int(bool(label)))
            classes[key] += 1
            for name, value in features.items():
                value = str(value)
                counts[name][key][value] += 1
                values[name].add(value)
        return cls(dict(classes), {name: {key: dict(counter) for key, counter in by_class.items()} for name, by_class in counts.items()}, {name: tuple(sorted(items)) for name, items in values.items()}, alpha)

    def predict(self, features: Mapping[str, str]) -> float:
        total = sum(self.class_counts.values())
        if not total:
            return 0.0
        logs: dict[str, float] = {}
        for klass in ("0", "1"):
            class_count = self.class_counts.get(klass, 0)
            logp = math.log((class_count + self.alpha) / (total + 2 * self.alpha))
            for name, value in features.items():
                values = set(self.feature_values.get(name, ())) | {str(value)}
                denominator = class_count + self.alpha * len(values)
                numerator = self.feature_counts.get(name, {}).get(klass, {}).get(str(value), 0) + self.alpha
                logp += math.log(numerator / denominator)
            logs[klass] = logp
        maximum = max(logs.values())
        p0, p1 = math.exp(logs["0"] - maximum), math.exp(logs["1"] - maximum)
        return _clamp(p1 / (p0 + p1))

    def to_dict(self) -> dict[str, object]:
        return {"class_counts": self.class_counts, "feature_counts": self.feature_counts, "feature_values": {name: list(values) for name, values in self.feature_values.items()}, "alpha": self.alpha}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CategoricalNaiveBayes":
        return cls(
            {str(k): int(v) for k, v in dict(data["class_counts"]).items()},
            {str(name): {str(k): {str(vk): int(vv) for vk, vv in dict(values).items()} for k, values in dict(by_class).items()} for name, by_class in dict(data["feature_counts"]).items()},
            {str(name): tuple(str(x) for x in values) for name, values in dict(data["feature_values"]).items()}, float(data.get("alpha", 1.0)),
        )


@dataclass(frozen=True)
class OpponentTileRisk:
    target_player: PlayerPosition
    tenpai_probability: float
    wait_probability_given_tenpai: float
    deal_in_probability: float


@dataclass(frozen=True)
class DiscardRiskPrediction:
    tile: int
    copies_in_hand: int
    opponent_risks: tuple[OpponentTileRisk, ...]
    combined_deal_in_probability: float


@dataclass(frozen=True)
class BayesianOpponentModel:
    tenpai_model: CategoricalNaiveBayes
    wait_model: CategoricalNaiveBayes
    global_wait_prior: float
    tile_wait_priors: tuple[float, ...]
    tenpai_prior: float
    training_metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "model_type": "bayesian_opponent_risk", "model_version": "0.6.0",
            "feature_version": {"tenpai": "tenpai_features_v1", "wait": "wait_features_v1"},
            "rule_version": "simplified_108", "tenpai_model": self.tenpai_model.to_dict(),
            "wait_model": self.wait_model.to_dict(),
            "baselines": {"global_wait_prior": self.global_wait_prior, "tile_wait_priors": list(self.tile_wait_priors), "tenpai_prior": self.tenpai_prior},
            "training_metadata": self.training_metadata,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "BayesianOpponentModel":
        if data.get("model_type") != "bayesian_opponent_risk":
            raise ValueError("不是 bayesian_opponent_risk 模型")
        baselines = data["baselines"]
        return cls(CategoricalNaiveBayes.from_dict(data["tenpai_model"]), CategoricalNaiveBayes.from_dict(data["wait_model"]), float(baselines["global_wait_prior"]), tuple(float(x) for x in baselines["tile_wait_priors"]), float(baselines["tenpai_prior"]), dict(data.get("training_metadata", {})))


def train_opponent_model(samples: Iterable[BayesianSample | Mapping[str, object]]) -> BayesianOpponentModel:
    rows = [_sample_dict(sample) for sample in samples]
    tenpai_rows = [(tenpai_features(public_context_from_sample(row)), int(bool(row["target_is_tenpai"]))) for row in rows]
    valid_waits = [row for row in rows if is_valid_wait_training_sample(row)]
    wait_rows = [(wait_features(public_context_from_sample(row), tile), label) for row in valid_waits for tile, label in expand_wait_samples(row)]
    if not tenpai_rows or not wait_rows:
        raise ValueError("训练需要至少一个样本以及一个有效听牌样本")
    positives = sum(label for _features, label in wait_rows)
    by_tile: list[list[int]] = [[] for _ in range(TILE_KIND_COUNT)]
    for row in valid_waits:
        for tile, label in expand_wait_samples(row):
            by_tile[tile].append(label)
    global_prior = positives / len(wait_rows)
    return BayesianOpponentModel(
        tenpai_model=CategoricalNaiveBayes.fit(tenpai_rows), wait_model=CategoricalNaiveBayes.fit(wait_rows),
        global_wait_prior=global_prior,
        tile_wait_priors=tuple(sum(values) / len(values) if values else global_prior for values in by_tile),
        tenpai_prior=sum(label for _features, label in tenpai_rows) / len(tenpai_rows),
        training_metadata={"sample_count": len(rows), "valid_wait_state_count": len(valid_waits), "wait_candidate_count": len(wait_rows), "wait_positive_count": positives, "wait_positive_rate": global_prior},
    )


def train_and_evaluate(samples: Iterable[BayesianSample | Mapping[str, object]]) -> BayesianOpponentModel:
    """Train on a deterministic game-id split and retain held-out reports."""
    rows = [_sample_dict(sample) for sample in samples]
    buckets: dict[str, list[dict[str, object]]] = {"train": [], "validation": [], "test": []}
    for row in rows:
        # No random split: the same JSONL always gives the same held-out groups.
        bucket = sum(ord(char) for char in str(row["game_id"])) % 10
        buckets["test" if bucket == 0 else "validation" if bucket == 1 else "train"].append(row)
    train_rows = buckets["train"] or rows
    model = train_opponent_model(train_rows)
    from .evaluation import evaluate_risk_model, evaluate_tenpai_models, evaluate_wait_models
    metadata = dict(model.training_metadata)
    metadata["split_counts"] = {name: len(items) for name, items in buckets.items()}
    metadata["held_out_evaluation"] = {
        name: {
            "tenpai": evaluate_tenpai_models(model, items),
            "wait": evaluate_wait_models(model, items),
            "risk": evaluate_risk_model(model, items),
        }
        for name, items in buckets.items() if name != "train" and items
    }
    return replace(model, training_metadata=metadata)


def _legal_discard_tiles(observation: Observation) -> tuple[int, ...]:
    # This is the same post-draw legal state enforced by MahjongEnvironment.
    if observation.current_player is not observation.player or observation.phase is not Phase.DISCARD or sum(observation.own_hand) % 3 != 2:
        return ()
    return tuple(tile for tile, count in enumerate(observation.own_hand) if count > 0)


def predict_discard_risks(model: BayesianOpponentModel, observation: Observation) -> tuple[DiscardRiskPrediction, ...]:
    """Predict only from ``Observation``; no full state is accepted or read."""
    predictions: list[DiscardRiskPrediction] = []
    for tile in _legal_discard_tiles(observation):
        risks: list[OpponentTileRisk] = []
        for target in PlayerPosition:
            if target is observation.player:
                continue
            context = public_context_from_observation(observation, target)
            tenpai = _clamp(model.tenpai_model.predict(tenpai_features(context)))
            wait = _clamp(model.wait_model.predict(wait_features(context, tile)))
            risks.append(OpponentTileRisk(target, tenpai, wait, _clamp(tenpai * wait)))
        combined = _clamp(1.0 - math.prod(1.0 - risk.deal_in_probability for risk in risks))
        predictions.append(DiscardRiskPrediction(tile, int(observation.own_hand[tile]), tuple(risks), combined))
    return tuple(sorted(predictions, key=lambda item: (item.combined_deal_in_probability, item.tile)))


def save_model(model: BayesianOpponentModel, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(model.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_model(path: str | Path) -> BayesianOpponentModel:
    return BayesianOpponentModel.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
