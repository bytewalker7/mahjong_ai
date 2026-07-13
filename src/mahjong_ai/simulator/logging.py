"""JSONL full-information game logs and deterministic replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ..state.models import PlayerPosition
from .environment import MahjongEnvironment
from .models import (
    Action, AddedGangAction, ConcealedGangAction, DiscardAction, DrawAction,
    ExposedGangAction, PassAction, PengAction, ReplacementDrawAction, RonAction,
    TsumoAction,
)


_ACTION_TYPES = {
    item.__name__: item
    for item in (DiscardAction, DrawAction, ReplacementDrawAction, PassAction,
                 PengAction, ExposedGangAction, ConcealedGangAction,
                 AddedGangAction, RonAction, TsumoAction)
}


def action_to_dict(action: Action) -> dict[str, object]:
    return {"type": type(action).__name__, "values": dict(action.__dict__)}


def action_from_dict(data: dict[str, object]) -> Action:
    try:
        action_type = _ACTION_TYPES[str(data["type"])]
        values = data.get("values", {})
        if not isinstance(values, dict):
            raise ValueError("action values must be an object")
        return action_type(**values)
    except (KeyError, TypeError) as error:
        raise ValueError("invalid action in full log") from error


def save_full_log(logs: Iterable[dict[str, object]] | dict[str, object], path: str | Path) -> None:
    """Write one complete game object per JSONL line."""
    items = [logs] if isinstance(logs, dict) else logs
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for log in items:
            handle.write(json.dumps(log, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_full_log(path: str | Path) -> list[dict[str, object]]:
    """Load JSONL game logs without mutating their contents."""
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def replay_full_log(log: dict[str, object]) -> MahjongEnvironment:
    """Replay recorded actions and verify the logged terminal result."""
    environment = MahjongEnvironment()
    environment.reset(int(log["seed"]))
    for data in log["actions"]:
        environment.step(action_from_dict(data))
    state = environment.full_state
    if state.result != log["final_result"] or (state.winner.name if state.winner is not None else None) != log["winner"]:
        raise ValueError("full log replay result does not match")
    return environment
