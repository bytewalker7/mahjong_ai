"""Convert the public state-engine view to the risk model observation format."""

from __future__ import annotations

from typing import Mapping

from ..meld import Meld, MeldType
from ..simulator.models import Observation, Phase
from ..state.models import GameState, PlayerPosition


def observation_from_game_state(state: GameState) -> Observation:
    """Create a public-only observation without inferring any hidden opponent tile."""
    awaiting_response = (
        state.last_discard is not None
        and state.last_discard.called_by is None
        and state.current_player is state.last_discard.player
    )
    if state.round_finished:
        phase = Phase.FINISHED
    elif awaiting_response:
        phase = Phase.RESPONSE
    elif state.players[state.current_player].concealed_tile_count % 3 == 2:
        phase = Phase.DISCARD
    else:
        phase = Phase.DRAW
    public_discards = tuple(
        tuple((discard.tile, discard.called_by is not None) for discard in state.players[position].discards)
        for position in PlayerPosition
    )
    public_melds = tuple(
        tuple(
            (meld.meld_type.value, meld.tile if position is PlayerPosition.SELF or meld.meld_type is not MeldType.CONCEALED_GANG else None)
            for meld in state.players[position].melds
        )
        for position in PlayerPosition
    )
    return Observation(
        player=PlayerPosition.SELF,
        own_hand=tuple(state.own_hand), own_melds=tuple(state.players[PlayerPosition.SELF].melds),
        public_discards=public_discards, public_melds=public_melds,
        visible_counts=tuple(state.visible_counts),
        concealed_tile_counts=tuple(state.players[position].concealed_tile_count for position in PlayerPosition),
        current_player=state.current_player, phase=phase, wall_remaining=state.wall_remaining,
        turn=len(state.events), last_discard_tile=state.last_discard.tile if state.last_discard else None,
    )


def observation_to_dict(observation: Observation) -> dict[str, object]:
    """JSON-safe form accepted by the ``predict-discard-risk`` CLI."""
    return {
        "player": observation.player.name, "own_hand": list(observation.own_hand),
        "own_melds": [{"meld_type": meld.meld_type.name, "tile": meld.tile, "from_player": meld.from_player} for meld in observation.own_melds],
        "public_discards": [[list(record) for record in player_discards] for player_discards in observation.public_discards],
        "public_melds": [[list(record) for record in player_melds] for player_melds in observation.public_melds],
        "visible_counts": list(observation.visible_counts), "concealed_tile_counts": list(observation.concealed_tile_counts),
        "current_player": observation.current_player.name, "phase": observation.phase.value,
        "wall_remaining": observation.wall_remaining, "turn": observation.turn,
        "last_discard_tile": observation.last_discard_tile,
    }


def observation_from_dict(data: Mapping[str, object]) -> Observation:
    """Read the documented JSON observation format."""
    def position(value: object) -> PlayerPosition:
        return PlayerPosition[str(value)]
    own_melds = tuple(
        Meld(MeldType[str(item["meld_type"])], int(item["tile"]), item.get("from_player"))
        for item in data.get("own_melds", [])
    )
    return Observation(
        player=position(data["player"]), own_hand=tuple(int(x) for x in data["own_hand"]), own_melds=own_melds,
        public_discards=tuple(tuple((int(tile), bool(used)) for tile, used in rows) for rows in data["public_discards"]),
        public_melds=tuple(tuple((str(kind), None if tile is None else int(tile)) for kind, tile in rows) for rows in data["public_melds"]),
        visible_counts=tuple(int(x) for x in data["visible_counts"]),
        concealed_tile_counts=tuple(int(x) for x in data["concealed_tile_counts"]),
        current_player=position(data["current_player"]), phase=Phase(str(data["phase"])),
        wall_remaining=int(data["wall_remaining"]), turn=int(data["turn"]),
        last_discard_tile=None if data.get("last_discard_tile") is None else int(data["last_discard_tile"]),
    )
