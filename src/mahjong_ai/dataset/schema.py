"""Serializable schema for one observer-target Bayesian training sample."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BayesianSample:
    game_id: str
    event_index: int
    observer: str
    target: str
    public_input: dict[str, object]
    target_shanten: int
    target_is_tenpai: bool
    target_wait_mask: tuple[bool, ...]
    target_danger_mask: tuple[bool, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "game_id": self.game_id,
            "event_index": self.event_index,
            "observer": self.observer,
            "target": self.target,
            "public_input": self.public_input,
            "target_shanten": self.target_shanten,
            "target_is_tenpai": self.target_is_tenpai,
            "target_wait_mask": list(self.target_wait_mask),
            "target_danger_mask": list(self.target_danger_mask),
        }
