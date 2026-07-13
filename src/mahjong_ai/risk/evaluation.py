"""Deterministic probability and grouped wait/risk evaluation helpers."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Callable, Iterable, Mapping

from .features import public_context_from_sample, tenpai_features, wait_features
from .model import BayesianOpponentModel, expand_wait_samples, is_valid_wait_training_sample


def probability_metrics(labels: Iterable[int], probabilities: Iterable[float]) -> dict[str, object]:
    pairs = [(int(label), max(0.0, min(1.0, float(probability)))) for label, probability in zip(labels, probabilities)]
    if not pairs:
        return {"count": 0, "positive_rate": 0.0, "brier_score": 0.0, "log_loss": 0.0, "calibration": []}
    eps = 1e-12
    calibration = []
    for index in range(10):
        lower, upper = index / 10, (index + 1) / 10
        bucket = [(label, prob) for label, prob in pairs if lower <= prob < upper or (index == 9 and prob == 1.0)]
        if bucket:
            calibration.append({"lower": lower, "upper": upper, "count": len(bucket), "mean_prediction": sum(prob for _label, prob in bucket) / len(bucket), "observed_rate": sum(label for label, _prob in bucket) / len(bucket)})
    return {
        "count": len(pairs), "positive_rate": sum(label for label, _prob in pairs) / len(pairs),
        "brier_score": sum((prob - label) ** 2 for label, prob in pairs) / len(pairs),
        "log_loss": -sum(label * math.log(max(prob, eps)) + (1 - label) * math.log(max(1 - prob, eps)) for label, prob in pairs) / len(pairs),
        "calibration": calibration,
    }


def evaluate_wait_models(model: BayesianOpponentModel, samples: Iterable[Mapping[str, object]]) -> dict[str, object]:
    grouped: dict[tuple[str, int, str, str], list[tuple[int, int, float, float, float]]] = defaultdict(list)
    for raw_row in samples:
        row = raw_row.to_dict() if hasattr(raw_row, "to_dict") else raw_row
        if not is_valid_wait_training_sample(row):
            continue
        context = public_context_from_sample(row)
        key = (str(row["game_id"]), int(row["event_index"]), str(row["observer"]), str(row["target"]))
        for tile, label in expand_wait_samples(row):
            grouped[key].append((tile, label, model.global_wait_prior, model.tile_wait_priors[tile], model.wait_model.predict(wait_features(context, tile))))
    def report(column: int) -> dict[str, object]:
        values = [entry for group in grouped.values() for entry in group]
        result = probability_metrics((entry[1] for entry in values), (entry[column] for entry in values))
        for k in (1, 3, 5):
            hits = 0
            for group in grouped.values():
                top = sorted(group, key=lambda entry: (-entry[column], entry[0]))[:k]
                hits += int(any(label for _tile, label, *_rest in top))
            result[f"top_{k}_recall"] = hits / len(grouped) if grouped else 0.0
        return result
    return {"global_wait_prior": report(2), "tile_prior": report(3), "naive_bayes_wait": report(4)}


def evaluate_tenpai_models(model: BayesianOpponentModel, samples: Iterable[Mapping[str, object]]) -> dict[str, object]:
    labels: list[int] = []
    global_predictions: list[float] = []
    naive_predictions: list[float] = []
    for raw_row in samples:
        row = raw_row.to_dict() if hasattr(raw_row, "to_dict") else raw_row
        labels.append(int(bool(row["target_is_tenpai"])))
        global_predictions.append(model.tenpai_prior)
        naive_predictions.append(model.tenpai_model.predict(tenpai_features(public_context_from_sample(row))))
    return {"global_tenpai_prior": probability_metrics(labels, global_predictions), "naive_bayes_tenpai": probability_metrics(labels, naive_predictions)}


def evaluate_risk_model(model: BayesianOpponentModel, samples: Iterable[Mapping[str, object]]) -> dict[str, object]:
    labels: list[int] = []
    probabilities: list[float] = []
    states: dict[tuple[str, int, str], list[tuple[int, int, float]]] = defaultdict(list)
    for raw_row in samples:
        row = raw_row.to_dict() if hasattr(raw_row, "to_dict") else raw_row
        danger = row.get("target_danger_mask", ())
        if not is_valid_wait_training_sample(row) or not isinstance(danger, (list, tuple)) or len(danger) != 27:
            continue
        context = public_context_from_sample(row)
        tenpai = model.tenpai_model.predict(tenpai_features(context))
        key = (str(row["game_id"]), int(row["event_index"]), str(row["observer"]))
        observer_hand = row["public_input"]["observer_hand"]
        for tile, label in expand_wait_samples(row):
            if int(observer_hand[tile]) <= 0:
                continue
            probability = tenpai * model.wait_model.predict(wait_features(context, tile))
            labels.append(int(bool(danger[tile])))
            probabilities.append(probability)
            states[key].append((tile, int(bool(danger[tile])), probability))
    result = probability_metrics(labels, probabilities)
    if states:
        safest = [min(group, key=lambda item: (item[2], item[0])) for group in states.values()]
        result["safest_tile_safe_hit_rate"] = sum(label == 0 for _tile, label, _prob in safest) / len(safest)
        result["top_3_safe_coverage"] = sum(any(label == 0 for _tile, label, _prob in sorted(group, key=lambda item: (item[2], item[0]))[:3]) for group in states.values()) / len(states)
    else:
        result["safest_tile_safe_hit_rate"] = result["top_3_safe_coverage"] = 0.0
    actual_danger = [prob for label, prob in zip(labels, probabilities) if label]
    actual_safe = [prob for label, prob in zip(labels, probabilities) if not label]
    result["actual_danger_mean_prediction"] = sum(actual_danger) / len(actual_danger) if actual_danger else 0.0
    result["actual_safe_mean_prediction"] = sum(actual_safe) / len(actual_safe) if actual_safe else 0.0
    return result
