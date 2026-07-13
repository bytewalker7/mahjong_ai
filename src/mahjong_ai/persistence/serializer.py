"""JSON persistence for game events; derived state is always replayed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..state import (
    AdvanceTurn, CallExposedGang, CallPeng, DeclareAddedGang,
    DeclareConcealedGang, DeclareWin, DiscardTile, DrawOwnTile, GameEvent,
    GameState, HiddenDraw, PlayerPosition, SetOwnInitialHand, StartRound,
    replay_events,
)

_EVENT_TYPES = {
    item.__name__: item
    for item in (
        AdvanceTurn, CallExposedGang, CallPeng, DeclareAddedGang,
        DeclareConcealedGang, DeclareWin, DiscardTile, DrawOwnTile,
        HiddenDraw, SetOwnInitialHand, StartRound,
    )
}


def save_state(path: str | Path, state: GameState) -> None:
    """Write only event facts to JSON; all state is reconstructed on load."""
    payload = {"version": 1, "events": [_event_to_dict(event) for event in state.events]}
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state(path: str | Path) -> GameState:
    """Load a saved event stream and validate it by replaying every event."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("events"), list):
        raise ValueError("unsupported or invalid Mahjong save file")
    return replay_events([_event_from_dict(item) for item in payload["events"]])


def _event_to_dict(event: GameEvent) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name, value in event.__dict__.items():
        if isinstance(value, PlayerPosition):
            values[name] = {"position": value.name}
        elif isinstance(value, tuple):
            values[name] = list(value)
        else:
            values[name] = value
    return {"type": type(event).__name__, "values": values}


def _event_from_dict(data: object) -> GameEvent:
    if not isinstance(data, dict) or not isinstance(data.get("type"), str) or not isinstance(data.get("values"), dict):
        raise ValueError("invalid event in save file")
    try:
        event_type = _EVENT_TYPES[data["type"]]
    except KeyError as error:
        raise ValueError(f"unknown event type {data['type']!r}") from error
    values = dict(data["values"])
    for name, value in values.items():
        if isinstance(value, dict) and set(value) == {"position"}:
            values[name] = PlayerPosition[value["position"]]
    if event_type is SetOwnInitialHand and isinstance(values.get("tiles"), list):
        values["tiles"] = tuple(values["tiles"])
    return event_type(**values)
