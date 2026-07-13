"""Immutable user actions recorded by the public-information state engine."""

from __future__ import annotations

from dataclasses import dataclass

from .models import PlayerPosition


@dataclass(frozen=True)
class StartRound:
    dealer: PlayerPosition


@dataclass(frozen=True)
class SetOwnInitialHand:
    tiles: tuple[int, ...]


@dataclass(frozen=True)
class DrawOwnTile:
    tile: int


@dataclass(frozen=True)
class HiddenDraw:
    player: PlayerPosition


@dataclass(frozen=True)
class DiscardTile:
    player: PlayerPosition
    tile: int


@dataclass(frozen=True)
class CallPeng:
    player: PlayerPosition
    tile: int
    from_player: PlayerPosition


@dataclass(frozen=True)
class CallExposedGang:
    player: PlayerPosition
    tile: int
    from_player: PlayerPosition


@dataclass(frozen=True)
class DeclareConcealedGang:
    player: PlayerPosition
    tile: int


@dataclass(frozen=True)
class DeclareAddedGang:
    player: PlayerPosition
    tile: int


@dataclass(frozen=True)
class DeclareWin:
    player: PlayerPosition


@dataclass(frozen=True)
class AdvanceTurn:
    """Resolve an uncalled discard and pass play to the next seat."""

    player: PlayerPosition


GameEvent = (
    StartRound
    | SetOwnInitialHand
    | DrawOwnTile
    | HiddenDraw
    | DiscardTile
    | CallPeng
    | CallExposedGang
    | DeclareConcealedGang
    | DeclareAddedGang
    | DeclareWin
    | AdvanceTurn
)
