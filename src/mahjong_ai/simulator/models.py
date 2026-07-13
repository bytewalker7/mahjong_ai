"""Full-information simulator data structures and player actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..meld import Meld
from ..state.models import PlayerPosition, RuleConfig


class Phase(Enum):
    DRAW = "draw"
    REPLACEMENT_DRAW = "replacement_draw"
    DISCARD = "discard"
    RESPONSE = "response"
    FINISHED = "finished"


@dataclass(frozen=True)
class DiscardAction:
    tile: int


@dataclass(frozen=True)
class DrawAction:
    pass


@dataclass(frozen=True)
class ReplacementDrawAction:
    pass


@dataclass(frozen=True)
class PassAction:
    pass


@dataclass(frozen=True)
class PengAction:
    pass


@dataclass(frozen=True)
class ExposedGangAction:
    pass


@dataclass(frozen=True)
class ConcealedGangAction:
    tile: int


@dataclass(frozen=True)
class AddedGangAction:
    tile: int


@dataclass(frozen=True)
class RonAction:
    pass


@dataclass(frozen=True)
class TsumoAction:
    pass


Action = (
    DiscardAction | DrawAction | ReplacementDrawAction | PassAction | PengAction
    | ExposedGangAction | ConcealedGangAction | AddedGangAction | RonAction | TsumoAction
)


@dataclass
class FullDiscardRecord:
    player: PlayerPosition
    tile: int
    called_by: PlayerPosition | None = None


@dataclass
class FullPlayerState:
    hand: list[int]
    melds: list[Meld] = field(default_factory=list)
    discards: list[FullDiscardRecord] = field(default_factory=list)


@dataclass
class FullGameState:
    rules: RuleConfig
    players: dict[PlayerPosition, FullPlayerState]
    wall: list[int]
    wall_index: int
    dealer: PlayerPosition
    current_player: PlayerPosition
    phase: Phase
    last_discard: FullDiscardRecord | None = None
    response_order: tuple[PlayerPosition, ...] = ()
    response_index: int = 0
    response_intents: list[tuple[PlayerPosition, Action]] = field(default_factory=list)
    winner: PlayerPosition | None = None
    result: str | None = None
    turn: int = 0
    events: list[dict[str, object]] = field(default_factory=list)

    @property
    def wall_remaining(self) -> int:
        return len(self.wall) - self.wall_index


@dataclass(frozen=True)
class Observation:
    player: PlayerPosition
    own_hand: tuple[int, ...]
    own_melds: tuple[Meld, ...]
    public_discards: tuple[tuple[tuple[int, bool], ...], ...]
    public_melds: tuple[tuple[tuple[str, int | None], ...], ...]
    visible_counts: tuple[int, ...]
    concealed_tile_counts: tuple[int, ...]
    current_player: PlayerPosition
    phase: Phase
    wall_remaining: int
    turn: int
    last_discard_tile: int | None


@dataclass(frozen=True)
class StepResult:
    observation: Observation
    done: bool
    event: dict[str, object]
