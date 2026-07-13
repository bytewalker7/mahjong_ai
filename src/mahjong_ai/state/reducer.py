"""Event reducer and replay-based undo for a public-information Mahjong round."""

from __future__ import annotations

from copy import deepcopy

from ..meld import Meld, MeldType
from ..tiles import TILE_KIND_COUNT, TileError, counts_from_codes
from .events import (
    AdvanceTurn,
    CallExposedGang,
    CallPeng,
    DeclareAddedGang,
    DeclareConcealedGang,
    DeclareWin,
    DiscardTile,
    DrawOwnTile,
    GameEvent,
    HiddenDraw,
    SetOwnInitialHand,
    StartRound,
)
from .models import DiscardRecord, GameState, PlayerPosition, PlayerState, RuleConfig
from .validation import StateValidationError, validate_state


def new_game(rules: RuleConfig | None = None) -> GameState:
    """Create an empty state; its first event must be :class:`StartRound`."""
    config = rules or RuleConfig()
    return GameState(
        rules=config,
        own_hand=[0] * TILE_KIND_COUNT,
        players={position: PlayerState(0) for position in PlayerPosition},
        current_player=PlayerPosition.SELF,
        dealer=PlayerPosition.SELF,
        wall_remaining=config.total_tiles,
        last_discard=None,
        visible_counts=[0] * TILE_KIND_COUNT,
        events=[],
    )


def apply_event(state: GameState, event: GameEvent) -> GameState:
    """Apply one event, validate all invariants, and append it to history."""
    next_state = _reduce_one(deepcopy(state), event)
    next_state.events.append(event)
    validate_state(next_state)
    return next_state


def replay_events(events: list[GameEvent], rules: RuleConfig | None = None) -> GameState:
    """Rebuild state solely from its immutable event history."""
    state = new_game(rules)
    for event in events:
        state = apply_event(state, event)
    return state


def undo_last_event(state: GameState) -> GameState:
    """Return the state before the most recent event, by replaying history."""
    if not state.events:
        raise StateValidationError("cannot undo an empty event history")
    return replay_events(state.events[:-1], state.rules)


def _require_active(state: GameState) -> None:
    if state.round_finished:
        raise StateValidationError("the round has already finished")


def _require_current(state: GameState, player: PlayerPosition) -> None:
    _require_active(state)
    if state.current_player is not player:
        raise StateValidationError(f"it is {state.current_player.name}'s turn, not {player.name}'s")


def _require_tile(tile: int) -> None:
    if not 0 <= tile < TILE_KIND_COUNT:
        raise TileError(f"tile code must be in 0..{TILE_KIND_COUNT - 1}")


def _remove_concealed(state: GameState, player: PlayerPosition, tile: int, amount: int) -> None:
    if state.players[player].concealed_tile_count < amount:
        raise StateValidationError(f"{player.name} does not have enough concealed tiles")
    if player is PlayerPosition.SELF:
        if state.own_hand[tile] < amount:
            raise StateValidationError("SELF does not hold the required tile")
        state.own_hand[tile] -= amount
    state.players[player].concealed_tile_count -= amount


def _add_meld(state: GameState, player: PlayerPosition, meld: Meld) -> None:
    if len(state.players[player].melds) >= 4:
        raise StateValidationError("a player cannot have more than four melds")
    state.players[player].melds.append(meld)


def _reduce_one(state: GameState, event: GameEvent) -> GameState:
    if isinstance(event, StartRound):
        if state.events:
            raise StateValidationError("StartRound must be the first event")
        state.dealer = event.dealer
        state.current_player = event.dealer
        for position in PlayerPosition:
            state.players[position] = PlayerState(14 if position is event.dealer else 13)
        state.wall_remaining = state.rules.total_tiles - 53
        return state

    if not state.events:
        raise StateValidationError("StartRound must be applied before other events")

    if isinstance(event, SetOwnInitialHand):
        if any(state.own_hand):
            raise StateValidationError("own initial hand has already been set")
        hand = counts_from_codes(event.tiles)
        expected = state.players[PlayerPosition.SELF].concealed_tile_count
        if sum(hand) != expected:
            raise StateValidationError(f"own initial hand must contain {expected} tiles")
        state.own_hand = hand
        return state

    if isinstance(event, DrawOwnTile):
        _require_current(state, PlayerPosition.SELF)
        _require_tile(event.tile)
        if state.wall_remaining == 0:
            raise StateValidationError("cannot draw from an empty wall")
        state.own_hand[event.tile] += 1
        state.players[PlayerPosition.SELF].concealed_tile_count += 1
        state.wall_remaining -= 1
        return state

    if isinstance(event, HiddenDraw):
        _require_current(state, event.player)
        if event.player is PlayerPosition.SELF:
            raise StateValidationError("use DrawOwnTile for SELF draws")
        if state.wall_remaining == 0:
            raise StateValidationError("cannot draw from an empty wall")
        state.players[event.player].concealed_tile_count += 1
        state.wall_remaining -= 1
        return state

    if isinstance(event, DiscardTile):
        _require_current(state, event.player)
        _require_tile(event.tile)
        _remove_concealed(state, event.player, event.tile, 1)
        record = DiscardRecord(event.player, event.tile)
        state.players[event.player].discards.append(record)
        state.last_discard = record
        state.visible_counts[event.tile] += 1
        return state

    if isinstance(event, CallPeng):
        _require_active(state)
        _require_tile(event.tile)
        _claim_last_discard(state, event.player, event.from_player, event.tile)
        _remove_concealed(state, event.player, event.tile, 2)
        _add_meld(state, event.player, Meld(MeldType.PENG, event.tile, event.from_player))
        state.visible_counts[event.tile] += 2
        state.current_player = event.player
        return state

    if isinstance(event, CallExposedGang):
        _require_active(state)
        _require_tile(event.tile)
        _claim_last_discard(state, event.player, event.from_player, event.tile)
        _remove_concealed(state, event.player, event.tile, 3)
        _add_meld(state, event.player, Meld(MeldType.EXPOSED_GANG, event.tile, event.from_player))
        state.visible_counts[event.tile] += 3
        state.current_player = event.player
        return state

    if isinstance(event, DeclareConcealedGang):
        _require_current(state, event.player)
        _require_tile(event.tile)
        _remove_concealed(state, event.player, event.tile, 4)
        _add_meld(state, event.player, Meld(MeldType.CONCEALED_GANG, event.tile))
        return state

    if isinstance(event, DeclareAddedGang):
        _require_current(state, event.player)
        _require_tile(event.tile)
        player = state.players[event.player]
        peng_index = next((index for index, meld in enumerate(player.melds) if meld.meld_type is MeldType.PENG and meld.tile == event.tile), None)
        if peng_index is None:
            raise StateValidationError("added gang requires an existing peng of the same tile")
        _remove_concealed(state, event.player, event.tile, 1)
        old_peng = player.melds[peng_index]
        player.melds[peng_index] = Meld(MeldType.ADDED_GANG, event.tile, old_peng.from_player)
        state.visible_counts[event.tile] += 1
        return state

    if isinstance(event, DeclareWin):
        _require_active(state)
        if event.player is not state.current_player:
            if state.last_discard is None or state.last_discard.called_by is not None:
                raise StateValidationError("only the current player may win without an available last discard")
        state.round_finished = True
        return state

    if isinstance(event, AdvanceTurn):
        _require_current(state, event.player)
        if state.last_discard is None or state.last_discard.player is not event.player:
            raise StateValidationError("AdvanceTurn requires the current player's uncalled discard")
        if state.last_discard.called_by is not None:
            raise StateValidationError("a called discard cannot advance normally")
        state.current_player = event.player.next_player()
        return state

    raise TypeError(f"unsupported event {event!r}")


def _claim_last_discard(state: GameState, caller: PlayerPosition, source: PlayerPosition, tile: int) -> None:
    discard = state.last_discard
    if discard is None or discard.player is not source or discard.tile != tile:
        raise StateValidationError("call must use the matching last discard")
    if discard.called_by is not None:
        raise StateValidationError("last discard has already been called")
    if caller is source:
        raise StateValidationError("a player cannot call their own discard")
    discard.called_by = caller
