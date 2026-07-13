from __future__ import annotations

from mahjong_ai.meld import MeldType
from mahjong_ai.rl.environment import DiscardRLEnvironment
from mahjong_ai.simulator.environment import MahjongEnvironment
from mahjong_ai.simulator.models import FullDiscardRecord
from mahjong_ai.state.models import PlayerPosition


def test_dealer_ron_and_tsumo_settlement_follow_rules_markdown() -> None:
    environment = MahjongEnvironment()
    environment.reset(1)
    state = environment.full_state
    state.dealer = PlayerPosition.SELF
    state.last_discard = FullDiscardRecord(PlayerPosition.LEFT, 0)
    environment._finish(PlayerPosition.SELF, "ron")
    assert state.scores[PlayerPosition.SELF] == 2
    assert state.scores[PlayerPosition.LEFT] == -2

    environment.reset(2)
    state = environment.full_state
    state.dealer = PlayerPosition.SELF
    environment._finish(PlayerPosition.SELF, "tsumo")
    assert state.scores[PlayerPosition.SELF] == 12
    assert all(state.scores[position] == -4 for position in PlayerPosition if position is not PlayerPosition.SELF)


def test_gang_and_paozi_scores_are_recorded() -> None:
    environment = MahjongEnvironment()
    environment.reset(3, {PlayerPosition.SELF: 3, PlayerPosition.LEFT: 1})
    environment._award_gang(PlayerPosition.SELF, MeldType.CONCEALED_GANG)
    environment._finish(PlayerPosition.SELF, "tsumo")
    assert environment.full_state.scores[PlayerPosition.SELF] == 11  # 6 tsumo + 2 gang + 3 own pao
    assert environment.full_state.scores[PlayerPosition.LEFT] == -3  # 2 tsumo payment + 1 pao


def test_rl_environment_exposes_only_masked_discard_decisions() -> None:
    environment = DiscardRLEnvironment(randomize_pao=False)
    step = environment.reset(101)
    assert len(step.features) == environment.feature_size
    while not step.done:
        tile = next(index for index, allowed in enumerate(step.legal_mask) if allowed)
        step = environment.step(tile)
    assert isinstance(step.score, int)
