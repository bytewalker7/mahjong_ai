"""Training and debugging commands for the public opponent-risk model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .model import load_model, predict_discard_risks, save_model, train_and_evaluate
from ..dataset.writer import load_samples
from .observation import observation_from_dict
from ..state.models import PlayerPosition
from ..tiles import code_to_tile

_POSITION_NAMES = {
    PlayerPosition.SELF: "自己", PlayerPosition.LEFT: "上家",
    PlayerPosition.OPPOSITE: "对家", PlayerPosition.RIGHT: "下家",
}


def train_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="训练公开信息麻将对手风险模型")
    parser.add_argument("--input", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    model = train_and_evaluate(load_samples(args.input))
    save_model(model, args.output)
    metadata = model.training_metadata
    print(f"模型已保存：{args.output}；等待牌正例比例：{float(metadata['wait_positive_rate']):.2%}")
    for name, report in metadata.get("held_out_evaluation", {}).items():
        wait = report["wait"]["naive_bayes_wait"]
        risk = report["risk"]
        print(f"{name}：Wait Brier={wait['brier_score']:.4f}，LogLoss={wait['log_loss']:.4f}，Risk Brier={risk['brier_score']:.4f}，Risk LogLoss={risk['log_loss']:.4f}")


def predict_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="预测每种弃牌的模型估计放炮概率")
    parser.add_argument("--model", required=True); parser.add_argument("--state", required=True)
    args = parser.parse_args(argv)
    model = load_model(args.model)
    observation = observation_from_dict(json.loads(Path(args.state).read_text(encoding="utf-8")))
    predictions = predict_discard_risks(model, observation)
    if not predictions:
        print("当前 Observation 不处于自己摸牌后的合法弃牌状态。")
        return
    for prediction in predictions:
        print(f"候选弃牌：{code_to_tile(prediction.tile)}（手中 {prediction.copies_in_hand} 张）")
        for risk in prediction.opponent_risks:
            print(f"  {_POSITION_NAMES[risk.target_player]}：听牌概率 {risk.tenpai_probability:.1%}；条件等待概率 {risk.wait_probability_given_tenpai:.1%}；模型估计放炮概率 {risk.deal_in_probability:.2%}")
        print(f"  任意一家综合模型估计放炮概率：{prediction.combined_deal_in_probability:.2%}\n")
    print("安全排序（条件独立近似；三家听牌和等待牌并非真正独立）：")
    for index, prediction in enumerate(predictions, 1):
        print(f"{index}. {code_to_tile(prediction.tile)}：{prediction.combined_deal_in_probability:.2%}")
