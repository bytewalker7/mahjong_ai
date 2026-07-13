"""State invariants shared by every reducer transition."""

from __future__ import annotations

from .models import GameState, MeldType, PlayerPosition
from ..tiles import TILE_KIND_COUNT, validate_counts


class StateValidationError(ValueError):
    """Raised when an event would produce an impossible public game state."""


def validate_state(state: GameState) -> None:
    """Check conservation, public-count, and local-hand invariants."""
    if set(state.players) != set(PlayerPosition):
        raise StateValidationError("state must contain exactly four player positions")
    if len(state.own_hand) != TILE_KIND_COUNT:
        raise StateValidationError("own_hand must contain 27 tile counts")
    try:
        validate_counts(state.own_hand)
        validate_counts(state.visible_counts)
    except ValueError as error:
        raise StateValidationError(str(error)) from error
    if state.wall_remaining < 0:
        raise StateValidationError("wall_remaining cannot be negative")
    own_hand_is_initialized = any(event.__class__.__name__ == "SetOwnInitialHand" for event in state.events)
    if own_hand_is_initialized and sum(state.own_hand) != state.players[PlayerPosition.SELF].concealed_tile_count:
        raise StateValidationError("own hand count must equal SELF concealed_tile_count")
    if any(player.concealed_tile_count < 0 for player in state.players.values()):
        raise StateValidationError("concealed tile counts cannot be negative")

    derived_visible = [0] * TILE_KIND_COUNT
    concealed_gangs = [0] * TILE_KIND_COUNT
    for position, player in state.players.items():
        for discard in player.discards:
            if discard.player is not position:
                raise StateValidationError("discard owner does not match its player state")
            if discard.called_by is None:
                derived_visible[discard.tile] += 1
        for meld in player.melds:
            if meld.meld_type is MeldType.CONCEALED_GANG:
                concealed_gangs[meld.tile] += meld.tile_count
            else:
                derived_visible[meld.tile] += meld.tile_count
    if derived_visible != state.visible_counts:
        raise StateValidationError("visible_counts does not match discards and exposed melds")

    known_by_tile = [state.own_hand[tile] + derived_visible[tile] + concealed_gangs[tile] for tile in range(TILE_KIND_COUNT)]
    if any(count > state.rules.copies_per_tile for count in known_by_tile):
        raise StateValidationError("a tile kind exceeds the configured copy limit")

    accounted = sum(player.concealed_tile_count for player in state.players.values())
    accounted += sum(derived_visible) + sum(concealed_gangs) + state.wall_remaining
    if accounted != state.rules.total_tiles:
        raise StateValidationError(f"tile conservation failed: expected {state.rules.total_tiles}, got {accounted}")
