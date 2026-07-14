from __future__ import annotations

from dataclasses import dataclass, field

from mahjong_ai.game.session import GameSession
from mahjong_ai.simulator.models import Action, Observation, RonAction, TsumoAction
from mahjong_ai.simulator.strategies import PlayerStrategy, RandomPlayer
from mahjong_ai.state.models import PlayerPosition


def test_new_game_preserves_running_scores() -> None:
    session = GameSession(seed=31)
    state = session.environment.full_state
    state.scores[PlayerPosition.SELF] = 7
    state.scores[PlayerPosition.LEFT] = -3
    state.scores[PlayerPosition.OPPOSITE] = -2
    state.scores[PlayerPosition.RIGHT] = -2

    session.new_game(seed=32)

    assert session.view().scores == {
        PlayerPosition.SELF: 7,
        PlayerPosition.LEFT: -3,
        PlayerPosition.OPPOSITE: -2,
        PlayerPosition.RIGHT: -2,
    }


@dataclass
class ObservationOnlyStrategy(PlayerStrategy):
    seen: list[Observation] = field(default_factory=list)

    def choose_action(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        assert isinstance(observation, Observation)
        assert not hasattr(observation, "wall")
        assert not hasattr(observation, "players")
        self.seen.append(observation)
        return next((action for action in legal_actions if isinstance(action, (RonAction, TsumoAction))), legal_actions[0])


def _strategies() -> dict[PlayerPosition, PlayerStrategy]:
    return {
        PlayerPosition.LEFT: RandomPlayer(11),
        PlayerPosition.OPPOSITE: RandomPlayer(22),
        PlayerPosition.RIGHT: RandomPlayer(33),
    }


def _play_to_end(session: GameSession) -> None:
    for _ in range(10_000):
        while session.advance_automatic_step():
            pass
        view = session.view()
        if view.finished:
            return
        legal = session.human_legal_actions()
        assert legal
        winning = next((action for action in legal if isinstance(action, (RonAction, TsumoAction))), None)
        session.apply_human_action(winning or legal[0])
    raise AssertionError("game did not finish")


def test_ai_receives_only_its_own_observation() -> None:
    spies = {position: ObservationOnlyStrategy() for position in (PlayerPosition.LEFT, PlayerPosition.OPPOSITE, PlayerPosition.RIGHT)}
    session = GameSession(seed=10, strategies=spies)
    _play_to_end(session)
    assert any(strategy.seen for strategy in spies.values())
    for position, strategy in spies.items():
        assert all(observation.player is position for observation in strategy.seen)


def test_human_public_view_has_no_ai_concealed_hands() -> None:
    session = GameSession(seed=20, strategies=_strategies())
    view = session.view()
    assert not hasattr(view, "hands")
    assert all(len(rows) == 0 for rows in view.observation.public_discards)
    assert len(view.observation.own_hand) == 27
    assert all(isinstance(count, int) for count in view.observation.concealed_tile_counts)


def test_seed_reproduces_session_and_all_actions_remain_legal() -> None:
    first = GameSession(seed=30, strategies=_strategies())
    second = GameSession(seed=30, strategies=_strategies())
    _play_to_end(first); _play_to_end(second)
    assert first.environment.full_state.events == second.environment.full_state.events
    assert first.view().finished and first.view().result in {"ron", "tsumo", "draw"}
    first.environment._validate()
    assert first.view().final_scores is not None
