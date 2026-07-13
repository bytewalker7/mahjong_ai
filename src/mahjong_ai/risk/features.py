"""Feature engineering shared by training and public-only prediction."""

from __future__ import annotations

from typing import Mapping

from ..simulator.models import Observation
from ..state.models import PlayerPosition
from ..tiles import TILE_KIND_COUNT


def relative_position(observer: str, target: str) -> int:
    """Return a stable public relative-seat code."""
    return (PlayerPosition[target] - PlayerPosition[observer]) % 4


def _nearby(visible: list[int], tile: int, offset: int) -> int:
    nearby = tile + offset
    if nearby < 0 or nearby >= TILE_KIND_COUNT or nearby // 9 != tile // 9:
        return -1  # Explicit out-of-suit / edge sentinel.
    return int(visible[nearby])


def _context(
    *, observer: str, target: str, observer_hand: list[int], visible: list[int],
    target_discards: list[int], target_melds: list[Mapping[str, object]],
    turn_bucket: int, target_concealed: int, stage: str,
) -> dict[str, object]:
    suit_discards = [sum(tile // 9 == suit for tile in target_discards) for suit in range(3)]
    meld_tiles = [meld.get("tile") for meld in target_melds]
    return {
        "observer": observer, "target": target, "observer_hand": observer_hand,
        "visible": visible, "target_discards": target_discards,
        "target_melds": target_melds, "turn_bucket": turn_bucket,
        "target_concealed": target_concealed, "stage": stage,
        "suit_discards": suit_discards, "meld_tiles": meld_tiles,
    }


def public_context_from_sample(sample: Mapping[str, object]) -> dict[str, object]:
    public = sample["public_input"]
    assert isinstance(public, Mapping)
    target = str(sample["target"])
    discards = public.get("discards", {})
    melds = public.get("melds", {})
    target_discards = [int(row["tile"]) for row in discards.get(target, [])]
    target_melds = list(melds.get(target, []))
    return _context(
        observer=str(sample["observer"]), target=target,
        observer_hand=[int(x) for x in public["observer_hand"]],
        visible=[int(x) for x in public["visible_counts"]],
        target_discards=target_discards, target_melds=target_melds,
        turn_bucket=int(public.get("turn_bucket", 0)),
        target_concealed=int(public.get("target_concealed_tile_count", 0)),
        stage=str(public.get("sample_stage", "unknown")),
    )


def public_context_from_observation(observation: Observation, target: PlayerPosition) -> dict[str, object]:
    names = [position.name for position in PlayerPosition]
    target_index = list(PlayerPosition).index(target)
    target_discards = [int(tile) for tile, _used in observation.public_discards[target_index]]
    target_melds = [
        {"type": meld_type, "tile": tile}
        for meld_type, tile in observation.public_melds[target_index]
    ]
    return _context(
        observer=observation.player.name, target=target.name,
        observer_hand=list(observation.own_hand), visible=list(observation.visible_counts),
        target_discards=target_discards, target_melds=target_melds,
        turn_bucket=min(observation.turn // 8, 13),
        target_concealed=int(observation.concealed_tile_counts[target_index]),
        stage=observation.phase.value,
    )


def tenpai_features(context: Mapping[str, object]) -> dict[str, str]:
    target_discards = list(context["target_discards"])
    return {
        "turn_bucket": str(context["turn_bucket"]),
        "target_meld_count": str(len(context["target_melds"])),
        "target_discard_count_bucket": str(min(len(target_discards) // 3, 6)),
        "target_concealed_tile_count": str(context["target_concealed"]),
        "relative_position": str(relative_position(str(context["observer"]), str(context["target"]))),
        "sample_stage": str(context["stage"]),
        "target_suit_discards": ",".join(str(min(int(x), 9)) for x in context["suit_discards"]),
    }


def wait_features(context: Mapping[str, object], tile: int) -> dict[str, str]:
    visible = list(context["visible"])
    target_discards = list(context["target_discards"])
    meld_tiles = list(context["meld_tiles"])
    suit, rank = divmod(tile, 9)
    features = tenpai_features(context)
    features.update({
        "candidate_suit": str(suit), "candidate_rank": str(rank + 1),
        "candidate_visible_count": str(visible[tile]),
        "observer_candidate_count": str(list(context["observer_hand"])[tile]),
        "target_discarded_same_tile_count": str(target_discards.count(tile)),
        "target_same_suit_discard_count": str(list(context["suit_discards"])[suit]),
        "target_meld_contains_same_tile": str(int(tile in meld_tiles)),
        "target_meld_contains_same_suit": str(int(any(isinstance(x, int) and x // 9 == suit for x in meld_tiles))),
        "nearby_visible_minus_2": str(_nearby(visible, tile, -2)),
        "nearby_visible_minus_1": str(_nearby(visible, tile, -1)),
        "nearby_visible_plus_1": str(_nearby(visible, tile, 1)),
        "nearby_visible_plus_2": str(_nearby(visible, tile, 2)),
    })
    return features
