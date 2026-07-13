"""Extract explainable public features and full-information labels."""

from __future__ import annotations

from .schema import BayesianSample
from ..state.models import PlayerPosition
from ..tiles import TILE_KIND_COUNT


def extract_samples(log: dict[str, object]) -> list[BayesianSample]:
    """Extract key decision snapshots without leaking target concealed tiles."""
    samples: list[BayesianSample] = []
    for event_index, event in enumerate(log["events"]):
        snapshot = event["snapshot"]
        if snapshot["phase"] not in {"discard", "response"}:
            continue
        for observer in PlayerPosition:
            for target in PlayerPosition:
                if target is observer:
                    continue
                public_input = _public_input(snapshot, observer, target)
                target_hand = snapshot["hands"][target.name]
                target_shanten = snapshot["shanten"][target.name]
                waits = set(snapshot["waits"][target.name])
                wait_mask = tuple(tile in waits for tile in range(TILE_KIND_COUNT))
                # Danger is meaningful only when the target is in a 13-tile
                # ready-to-win shape.  During a 14-tile discard decision, no
                # hypothetical post-discard hand is smuggled into the label.
                danger_mask = wait_mask if sum(target_hand) % 3 == 1 else (False,) * TILE_KIND_COUNT
                samples.append(BayesianSample(
                    game_id=str(log["game_id"]),
                    event_index=event_index,
                    observer=observer.name,
                    target=target.name,
                    public_input=public_input,
                    target_shanten=int(target_shanten),
                    target_is_tenpai=int(target_shanten) == 0,
                    target_wait_mask=wait_mask,
                    target_danger_mask=danger_mask,
                ))
    return samples


def _public_input(snapshot: dict[str, object], observer: PlayerPosition, target: PlayerPosition) -> dict[str, object]:
    discards = snapshot["discards"]
    melds = snapshot["melds"]
    hands = snapshot["hands"]
    sanitized_melds: dict[str, list[dict[str, object]]] = {}
    for position in PlayerPosition:
        records: list[dict[str, object]] = []
        for meld in melds[position.name]:
            record = dict(meld)
            if record["type"] == "concealed_gang" and position is not observer:
                record["tile"] = None
            records.append(record)
        sanitized_melds[position.name] = records
    target_discards = discards[target.name]
    suit_counts = [sum(1 for discard in target_discards if discard["tile"] // 9 == suit) for suit in range(3)]
    recent = [discard["tile"] // 9 for position in PlayerPosition for discard in discards[position.name][-3:]][-6:]
    candidate_features = [
        {
            "candidate_visible_count": snapshot["visible_counts"][tile],
            "observer_candidate_count": hands[observer.name][tile],
            "target_discarded_same_tile_count": sum(1 for discard in target_discards if discard["tile"] == tile),
            "nearby_visible_counts": [snapshot["visible_counts"][near] if 0 <= near < TILE_KIND_COUNT and near // 9 == tile // 9 else 0 for near in (tile - 1, tile, tile + 1)],
            "target_same_suit_discard_count": suit_counts[tile // 9],
        }
        for tile in range(TILE_KIND_COUNT)
    ]
    return {
        "observer_hand": list(hands[observer.name]),
        "discards": discards,
        "melds": sanitized_melds,
        "turn_bucket": min(int(snapshot["turn"]) // 8, 13),
        "visible_counts": snapshot["visible_counts"],
        "concealed_tile_counts": {position.name: sum(hands[position.name]) for position in PlayerPosition},
        "current_player": snapshot["current_player"],
        "target_meld_count": len(melds[target.name]),
        "target_discard_count": len(target_discards),
        "target_suit_discard_counts": suit_counts,
        "recent_discard_suits": recent,
        "target_concealed_tile_count": sum(hands[target.name]),
        "candidate_features": candidate_features,
    }
