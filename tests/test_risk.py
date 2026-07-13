from __future__ import annotations

import pytest

from mahjong_ai.dataset.schema import BayesianSample
from mahjong_ai.risk.evaluation import evaluate_wait_models, probability_metrics
from mahjong_ai.risk.features import wait_features
from mahjong_ai.risk.model import (
    expand_wait_samples,
    is_valid_wait_training_sample,
    load_model,
    predict_discard_risks,
    save_model,
    train_opponent_model,
)
from mahjong_ai.simulator.models import Observation, Phase
from mahjong_ai.state.models import PlayerPosition


def _sample(*, tenpai: bool = True, concealed: int = 13, waits: tuple[int, ...] = (6,)) -> BayesianSample:
    hand = [0] * 27
    hand[0], hand[1], hand[2], hand[3], hand[4], hand[6] = 1, 4, 4, 2, 2, 1
    mask = tuple(tile in waits for tile in range(27))
    danger = mask if tenpai and concealed % 3 == 1 else (False,) * 27
    public = {
        "observer_hand": hand,
        "visible_counts": [0] * 27,
        "discards": {"SELF": [], "LEFT": [{"tile": 2}], "OPPOSITE": [], "RIGHT": []},
        "melds": {"SELF": [], "LEFT": [], "OPPOSITE": [], "RIGHT": []},
        "turn_bucket": 2, "sample_stage": "response", "target_concealed_tile_count": concealed,
    }
    return BayesianSample("game-a", 3, "SELF", "LEFT", public, 0 if tenpai else 1, tenpai, mask, danger)


def _observation() -> Observation:
    hand = [0] * 27
    hand[0], hand[1], hand[2], hand[3], hand[4], hand[6] = 1, 4, 4, 2, 2, 1
    return Observation(
        player=PlayerPosition.SELF, own_hand=tuple(hand), own_melds=(),
        public_discards=((), ((2, False),), (), ()), public_melds=((), (), (), ()),
        visible_counts=(0,) * 27, concealed_tile_counts=(14, 13, 13, 13),
        current_player=PlayerPosition.SELF, phase=Phase.DISCARD,
        wall_remaining=50, turn=16, last_discard_tile=None,
    )


def test_wait_training_filters_and_expansion() -> None:
    valid = _sample()
    assert is_valid_wait_training_sample(valid)
    assert len(expand_wait_samples(valid)) == 27
    assert dict(expand_wait_samples(valid))[6] == 1
    assert not is_valid_wait_training_sample(_sample(concealed=14))
    assert not is_valid_wait_training_sample(_sample(tenpai=False))
    malformed = valid.to_dict(); malformed["target_wait_mask"] = [False] * 26
    assert not is_valid_wait_training_sample(malformed)


def test_wait_features_do_not_cross_suit_edges() -> None:
    context = {
        "observer": "SELF", "target": "LEFT", "observer_hand": [0] * 27,
        "visible": [0] * 27, "target_discards": [], "target_melds": [],
        "turn_bucket": 0, "target_concealed": 13, "stage": "response",
        "suit_discards": [0, 0, 0], "meld_tiles": [],
    }
    features = wait_features(context, 0)
    assert features["nearby_visible_minus_1"] == "-1"
    assert features["nearby_visible_minus_2"] == "-1"
    assert features["nearby_visible_plus_1"] == "0"


def test_public_risk_prediction_save_load_and_sorting(tmp_path) -> None:
    model = train_opponent_model([_sample(), _sample(waits=(0, 3)), _sample(tenpai=False)])
    observation = _observation()
    before = predict_discard_risks(model, observation)
    assert [item.tile for item in before] == sorted(item.tile for item in before) or all(before[i].combined_deal_in_probability <= before[i + 1].combined_deal_in_probability for i in range(len(before)-1))
    assert {item.tile for item in before} == {0, 1, 2, 3, 4, 6}
    assert next(item for item in before if item.tile == 3).copies_in_hand == 2
    for prediction in before:
        assert len(prediction.opponent_risks) == 3
        assert 0 <= prediction.combined_deal_in_probability <= 1
        assert prediction.combined_deal_in_probability >= max(risk.deal_in_probability for risk in prediction.opponent_risks)
        for risk in prediction.opponent_risks:
            assert risk.deal_in_probability == risk.tenpai_probability * risk.wait_probability_given_tenpai
    path = tmp_path / "model.json"; save_model(model, path)
    assert predict_discard_risks(load_model(path), observation) == before
    assert observation.own_hand == _observation().own_hand


def test_prediction_requires_legal_discard_state() -> None:
    model = train_opponent_model([_sample(), _sample(tenpai=False)])
    observation = _observation()
    blocked = Observation(**{**observation.__dict__, "phase": Phase.RESPONSE})
    assert predict_discard_risks(model, blocked) == ()


def test_metrics_and_grouped_top_k_are_well_formed() -> None:
    model = train_opponent_model([_sample(), _sample(waits=(0, 3)), _sample(tenpai=False)])
    report = evaluate_wait_models(model, [_sample(), _sample(waits=(0, 3))])
    assert set(report) == {"global_wait_prior", "tile_prior", "naive_bayes_wait"}
    assert 0 <= report["naive_bayes_wait"]["top_3_recall"] <= 1
    metrics = probability_metrics([0, 1], [0.1, 0.9])
    assert metrics["brier_score"] == pytest.approx(0.01)
    assert metrics["log_loss"] > 0
