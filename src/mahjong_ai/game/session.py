"""Controller between the reusable simulator and the desktop game UI."""

from __future__ import annotations

from dataclasses import dataclass

from .ai_player import AIPlayer
from .human_player import HumanPlayer
from ..simulator.environment import MahjongEnvironment
from ..simulator.models import Action, DrawAction, Observation, Phase, ReplacementDrawAction
from ..simulator.strategies import HeuristicPlayer, NoisyHeuristicPlayer, PlayerStrategy
from ..state.models import PlayerPosition


@dataclass(frozen=True)
class PublicGameView:
    """Everything the human UI may render; it deliberately excludes AI hands."""

    observation: Observation
    finished: bool
    winner: PlayerPosition | None
    result: str | None
    final_scores: dict[PlayerPosition, int] | None
    drawn_tile: int | None
    dealer: PlayerPosition
    last_discard_player: PlayerPosition | None


class GameSession:
    """One human SELF seat and three independent AI seats.

    Game state changes exclusively through ``MahjongEnvironment.step``.  Each
    AI receives a fresh seat-specific Observation; it never receives
    FullGameState, another AI's observation, or another AI's decision data.
    """

    human_position = PlayerPosition.SELF

    def __init__(self, *, seed: int | None = None, strategies: dict[PlayerPosition, PlayerStrategy] | None = None) -> None:
        self._seed = seed
        self._environment = MahjongEnvironment()
        self._human = HumanPlayer()
        self._ais = self._build_ai_players(seed, strategies)
        self.new_game(seed)

    @property
    def environment(self) -> MahjongEnvironment:
        """Controller-only hook for tests; the UI must use :meth:`view`."""
        return self._environment

    def _build_ai_players(self, seed: int | None, supplied: dict[PlayerPosition, PlayerStrategy] | None) -> dict[PlayerPosition, AIPlayer]:
        if supplied is None:
            base = 0 if seed is None else seed
            supplied = {
                PlayerPosition.LEFT: HeuristicPlayer(base + 101),
                PlayerPosition.OPPOSITE: NoisyHeuristicPlayer(base + 211, temperature=0.75),
                PlayerPosition.RIGHT: NoisyHeuristicPlayer(base + 307, temperature=1.25),
            }
        expected = set(PlayerPosition) - {self.human_position}
        if set(supplied) != expected:
            raise ValueError("exactly three non-human AI strategies are required")
        return {position: AIPlayer(position, strategy) for position, strategy in supplied.items()}

    def new_game(self, seed: int | None = None) -> PublicGameView:
        self._seed = seed
        self._environment.reset(seed, {position: 0 for position in PlayerPosition})
        return self.view()

    def view(self) -> PublicGameView:
        observation = self._environment.observation(self.human_position)
        state = self._environment.full_state
        drawn_tile: int | None = None
        if state.events:
            last_event = state.events[-1]
            if last_event["player"] == self.human_position.name and last_event["kind"] in {"draw", "replacement_draw"}:
                drawn_tile = last_event["tile"]
        return PublicGameView(
            observation=observation, finished=state.phase is Phase.FINISHED,
            winner=state.winner, result=state.result,
            final_scores={position: state.scores[position] for position in PlayerPosition} if state.phase is Phase.FINISHED else None,
            drawn_tile=drawn_tile,
            dealer=state.dealer,
            last_discard_player=state.last_discard.player if state.last_discard is not None and state.last_discard.called_by is None else None,
        )

    def human_legal_actions(self) -> tuple[Action, ...]:
        view = self.view()
        if view.finished or view.observation.current_player is not self.human_position:
            return ()
        return self._environment.legal_actions()

    def apply_human_action(self, action: Action) -> PublicGameView:
        view = self.view()
        legal = self.human_legal_actions()
        self._human.validate_action(view.observation, action, legal)
        self._environment.step(action)
        return self.view()

    def advance_automatic_step(self) -> bool:
        """Execute exactly one forced draw or one AI action; return whether one ran."""
        state = self._environment.full_state
        if state.phase is Phase.FINISHED:
            return False
        player = state.current_player
        legal = self._environment.legal_actions()
        if not legal:
            return False
        if player is self.human_position:
            if state.phase is Phase.DRAW:
                self._environment.step(DrawAction())
                return True
            if state.phase is Phase.REPLACEMENT_DRAW:
                self._environment.step(ReplacementDrawAction())
                return True
            return False
        observation = self._environment.observation(player)
        action = self._ais[player].choose_action(observation, legal)
        if action not in legal:
            raise ValueError("AI strategy returned an illegal action")
        self._environment.step(action)
        return True
