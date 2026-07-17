"""Four-player, full-information simulator using the project's tile algorithms."""

from __future__ import annotations

import random
from copy import deepcopy

from ..meld import Meld, MeldType
from ..shanten import calculate_shanten
from ..state.models import PlayerPosition, RuleConfig
from ..tiles import COPIES_PER_TILE, TILE_KIND_COUNT
from .models import (
    Action, AddedGangAction, ConcealedGangAction, DiscardAction, DrawAction,
    ExposedGangAction, FullDiscardRecord, FullGameState, FullPlayerState,
    Observation, PassAction, PengAction, Phase, ReplacementDrawAction,
    RonAction, StepResult, TsumoAction,
)
from .scoring import ScoreRules, empty_scores


class MahjongEnvironment:
    """A deterministic environment; strategies receive only :class:`Observation`."""

    def __init__(
        self,
        rules: RuleConfig | None = None,
        score_rules: ScoreRules | None = None,
        *,
        record_full_snapshots: bool = True,
    ) -> None:
        self.rules = rules or RuleConfig()
        self.score_rules = score_rules or ScoreRules()
        self.record_full_snapshots = record_full_snapshots
        self._rng = random.Random()
        self._state: FullGameState | None = None

    @property
    def full_state(self) -> FullGameState:
        if self._state is None:
            raise RuntimeError("call reset() before reading full_state")
        return self._state

    def reset(
        self,
        seed: int | None = None,
        pao_counts: dict[PlayerPosition, int] | None = None,
        initial_scores: dict[PlayerPosition, int] | None = None,
    ) -> Observation:
        self._rng = random.Random(seed)
        dealer = self._rng.choice(tuple(PlayerPosition))
        deck = [tile for tile in range(TILE_KIND_COUNT) for _ in range(COPIES_PER_TILE)]
        self._rng.shuffle(deck)
        players = {position: FullPlayerState([0] * TILE_KIND_COUNT) for position in PlayerPosition}
        index = 0
        for _ in range(13):
            for position in PlayerPosition:
                players[position].hand[deck[index]] += 1
                index += 1
        players[dealer].hand[deck[index]] += 1
        index += 1
        self._state = FullGameState(
            rules=self.rules,
            players=players,
            wall=deck[index:],
            wall_index=0,
            dealer=dealer,
            current_player=dealer,
            phase=Phase.DISCARD,
            score_rules=self.score_rules,
            scores=(initial_scores or empty_scores()).copy(),
            pao_counts=self._validated_pao_counts(pao_counts),
        )
        self._record("start", dealer, None)
        self._validate()
        return self.observation(dealer)

    def observation(self, player: PlayerPosition) -> Observation:
        state = self.full_state
        visible = self._visible_counts()
        discards = tuple(tuple((record.tile, record.called_by is not None) for record in state.players[position].discards) for position in PlayerPosition)
        melds: list[tuple[tuple[str, int | None], ...]] = []
        for position in PlayerPosition:
            items: list[tuple[str, int | None]] = []
            for meld in state.players[position].melds:
                tile = None if meld.meld_type is MeldType.CONCEALED_GANG and position is not player else meld.tile
                items.append((meld.meld_type.value, tile))
            melds.append(tuple(items))
        return Observation(
            player=player,
            own_hand=tuple(state.players[player].hand),
            own_melds=tuple(state.players[player].melds),
            public_discards=discards,
            public_melds=tuple(melds),
            visible_counts=tuple(visible),
            concealed_tile_counts=tuple(sum(state.players[position].hand) for position in PlayerPosition),
            current_player=state.current_player,
            phase=state.phase,
            wall_remaining=state.wall_remaining,
            turn=state.turn,
            last_discard_tile=state.last_discard.tile if state.last_discard is not None and state.last_discard.called_by is None else None,
            dealer=state.dealer,
        )

    def legal_actions(self) -> tuple[Action, ...]:
        state = self.full_state
        if state.phase is Phase.FINISHED:
            return ()
        player = state.current_player
        hand = state.players[player].hand
        if state.phase is Phase.DRAW:
            return (DrawAction(),) if state.wall_remaining else ()
        if state.phase is Phase.REPLACEMENT_DRAW:
            return (ReplacementDrawAction(),) if state.wall_remaining else ()
        if state.phase is Phase.DISCARD:
            actions: list[Action] = [DiscardAction(tile) for tile, count in enumerate(hand) if count]
            fixed = len(state.players[player].melds)
            if calculate_shanten(hand, fixed) == -1:
                actions.append(TsumoAction())
            actions.extend(ConcealedGangAction(tile) for tile, count in enumerate(hand) if count >= 4)
            actions.extend(AddedGangAction(meld.tile) for meld in state.players[player].melds if meld.meld_type is MeldType.PENG and hand[meld.tile])
            return tuple(actions)
        if state.phase is Phase.RESPONSE:
            assert state.last_discard is not None
            tile = state.last_discard.tile
            actions = [PassAction()]
            if self._can_win_with(player, tile):
                actions.append(RonAction())
            if hand[tile] >= 2:
                actions.append(PengAction())
            if hand[tile] >= 3:
                actions.append(ExposedGangAction())
            return tuple(actions)
        raise AssertionError("unknown phase")

    def step(self, action: Action) -> StepResult:
        state = self.full_state
        before_scores = state.scores.copy()
        if action not in self.legal_actions():
            raise ValueError(f"illegal action {action!r} in {state.phase.value}")
        player = state.current_player
        if isinstance(action, DrawAction):
            self._draw(player, "draw")
        elif isinstance(action, ReplacementDrawAction):
            self._draw(player, "replacement_draw")
        elif isinstance(action, DiscardAction):
            state.players[player].hand[action.tile] -= 1
            record = FullDiscardRecord(player, action.tile)
            state.players[player].discards.append(record)
            state.last_discard = record
            state.response_order = self._response_order(player)
            state.response_index = 0
            state.response_intents.clear()
            state.current_player = state.response_order[0]
            state.phase = Phase.RESPONSE
            self._record("discard", player, action.tile)
        elif isinstance(action, ConcealedGangAction):
            state.players[player].hand[action.tile] -= 4
            state.players[player].melds.append(Meld(MeldType.CONCEALED_GANG, action.tile))
            self._award_gang(player, MeldType.CONCEALED_GANG)
            state.phase = Phase.REPLACEMENT_DRAW
            self._record("concealed_gang", player, action.tile)
            if state.wall_remaining == 0:
                self._finish(None, "draw")
        elif isinstance(action, AddedGangAction):
            melds = state.players[player].melds
            index = next(index for index, meld in enumerate(melds) if meld.meld_type is MeldType.PENG and meld.tile == action.tile)
            old = melds[index]
            state.players[player].hand[action.tile] -= 1
            melds[index] = Meld(MeldType.ADDED_GANG, action.tile, old.from_player)
            self._award_gang(player, MeldType.ADDED_GANG)
            state.phase = Phase.REPLACEMENT_DRAW
            self._record("added_gang", player, action.tile)
            if state.wall_remaining == 0:
                self._finish(None, "draw")
        elif state.phase is Phase.RESPONSE:
            state.response_intents.append((player, action))
            self._record(type(action).__name__, player, state.last_discard.tile if state.last_discard else None)
            state.response_index += 1
            if state.response_index < len(state.response_order):
                state.current_player = state.response_order[state.response_index]
            else:
                self._resolve_responses()
        elif isinstance(action, TsumoAction):
            self._finish(player, "tsumo")
        else:
            raise AssertionError("unhandled action")
        self._validate()
        return StepResult(
            self.observation(self.full_state.current_player), self.full_state.phase is Phase.FINISHED,
            deepcopy(self.full_state.events[-1]),
            tuple(self.full_state.scores[position] - before_scores[position] for position in PlayerPosition),
        )

    def _draw(self, player: PlayerPosition, kind: str) -> None:
        state = self.full_state
        if state.wall_remaining == 0:
            self._finish(None, "draw")
            return
        tile = state.wall[state.wall_index]
        state.wall_index += 1
        state.players[player].hand[tile] += 1
        state.phase = Phase.DISCARD
        state.turn += 1
        self._record(kind, player, tile)

    def _resolve_responses(self) -> None:
        state = self.full_state
        assert state.last_discard is not None
        source = state.last_discard.player
        intents = state.response_intents
        for action_type in (RonAction, ExposedGangAction, PengAction):
            for player in state.response_order:
                if any(actor is player and isinstance(action, action_type) for actor, action in intents):
                    if action_type is RonAction:
                        self._finish(player, "ron")
                        return
                    tile = state.last_discard.tile
                    state.last_discard.called_by = player
                    remove = 3 if action_type is ExposedGangAction else 2
                    state.players[player].hand[tile] -= remove
                    meld_type = MeldType.EXPOSED_GANG if action_type is ExposedGangAction else MeldType.PENG
                    state.players[player].melds.append(Meld(meld_type, tile, source))
                    if meld_type is MeldType.EXPOSED_GANG:
                        self._award_gang(player, meld_type)
                    state.current_player = player
                    if action_type is ExposedGangAction:
                        if state.wall_remaining == 0:
                            state.phase = Phase.REPLACEMENT_DRAW
                            self._record(meld_type.value, player, tile, source)
                            self._finish(None, "draw")
                        else:
                            state.phase = Phase.REPLACEMENT_DRAW
                            self._record(meld_type.value, player, tile, source)
                    else:
                        state.phase = Phase.DISCARD
                        self._record(meld_type.value, player, tile, source)
                    return
        next_player = source.next_player()
        state.current_player = next_player
        if state.wall_remaining == 0:
            self._finish(None, "draw")
        else:
            state.phase = Phase.DRAW
            self._record("advance", next_player, None)

    def _finish(self, winner: PlayerPosition | None, result: str) -> None:
        state = self.full_state
        state.winner = winner
        state.result = result
        if winner is not None:
            self._settle_hu(winner, result)
            self._settle_paozi(winner)
        state.phase = Phase.FINISHED
        self._record("finish", winner, None)

    def _award_gang(self, player: PlayerPosition, meld_type: MeldType) -> None:
        """Rules specify a direct gang gain; no gang payer is specified."""
        points = self.score_rules.gang_points(meld_type)
        self.full_state.scores[player] += points
        self.full_state.score_transactions.append({"kind": meld_type.value, "player": player.name, "points": points})

    def _settle_hu(self, winner: PlayerPosition, result: str) -> None:
        state = self.full_state
        multiplier = self.score_rules.dealer_hu_multiplier if winner is state.dealer else 1
        if result == "ron":
            assert state.last_discard is not None
            points = self.score_rules.ron_points * multiplier
            payer = state.last_discard.player
            state.scores[winner] += points
            state.scores[payer] -= points
            state.score_transactions.append({"kind": "ron", "winner": winner.name, "payer": payer.name, "points": points})
        elif result == "tsumo":
            payment = self.score_rules.tsumo_payment * multiplier
            for payer in PlayerPosition:
                if payer is not winner:
                    state.scores[payer] -= payment
                    state.scores[winner] += payment
            state.score_transactions.append({"kind": "tsumo", "winner": winner.name, "payment_per_opponent": payment})

    def _settle_paozi(self, winner: PlayerPosition) -> None:
        state = self.full_state
        # rules.markdown: each player's own paozi is an extra +/- one point.
        for player, count in state.pao_counts.items():
            points = int(count)
            state.scores[player] += points if player is winner else -points
        state.score_transactions.append({"kind": "paozi", "winner": winner.name, "counts": {player.name: count for player, count in state.pao_counts.items()}})

    def _validated_pao_counts(self, counts: dict[PlayerPosition, int] | None) -> dict[PlayerPosition, int]:
        result = {position: 0 for position in PlayerPosition}
        if counts is not None:
            for position, count in counts.items():
                if position not in result or not isinstance(count, int) or not 0 <= count <= self.score_rules.max_pao_count:
                    raise ValueError("pao count must be an integer in 0..4 for each player")
                result[position] = count
        return result

    def _can_win_with(self, player: PlayerPosition, tile: int) -> bool:
        hand = self.full_state.players[player].hand.copy()
        if hand[tile] >= COPIES_PER_TILE:
            return False
        hand[tile] += 1
        return calculate_shanten(hand, len(self.full_state.players[player].melds)) == -1

    @staticmethod
    def _response_order(source: PlayerPosition) -> tuple[PlayerPosition, ...]:
        result: list[PlayerPosition] = []
        current = source.next_player()
        for _ in range(3):
            result.append(current)
            current = current.next_player()
        return tuple(result)

    def _record(self, kind: str, player: PlayerPosition | None, tile: int | None, source: PlayerPosition | None = None) -> None:
        event = {
            "kind": kind,
            "player": player.name if player is not None else None,
            "tile": tile,
            "source": source.name if source is not None else None,
        }
        if self.record_full_snapshots:
            event["snapshot"] = self.full_snapshot()
        self.full_state.events.append(event)

    def full_snapshot(self) -> dict[str, object]:
        state = self.full_state
        return {
            "phase": state.phase.value,
            "turn": state.turn,
            "current_player": state.current_player.name,
            "wall_remaining": state.wall_remaining,
            "hands": {position.name: state.players[position].hand.copy() for position in PlayerPosition},
            "melds": {position.name: [{"type": meld.meld_type.value, "tile": meld.tile, "from": meld.from_player.name if meld.from_player is not None else None} for meld in state.players[position].melds] for position in PlayerPosition},
            "discards": {position.name: [{"tile": discard.tile, "called_by": discard.called_by.name if discard.called_by is not None else None} for discard in state.players[position].discards] for position in PlayerPosition},
            "visible_counts": self._visible_counts(),
            "shanten": {position.name: calculate_shanten(state.players[position].hand, len(state.players[position].melds)) for position in PlayerPosition},
            "is_tenpai": {position.name: calculate_shanten(state.players[position].hand, len(state.players[position].melds)) == 0 for position in PlayerPosition},
            "waits": {position.name: list(self._waits(position)) for position in PlayerPosition},
            "scores": {position.name: state.scores[position] for position in PlayerPosition},
            "pao_counts": {position.name: state.pao_counts[position] for position in PlayerPosition},
        }

    def _waits(self, player: PlayerPosition) -> tuple[int, ...]:
        state = self.full_state
        hand = state.players[player].hand
        if sum(hand) % 3 != 1 or calculate_shanten(hand, len(state.players[player].melds)) != 0:
            return ()
        result: list[int] = []
        for tile, count in enumerate(hand):
            if count >= COPIES_PER_TILE:
                continue
            hand[tile] += 1
            if calculate_shanten(hand, len(state.players[player].melds)) == -1:
                result.append(tile)
            hand[tile] -= 1
        return tuple(result)

    def _visible_counts(self) -> list[int]:
        counts = [0] * TILE_KIND_COUNT
        for player in self.full_state.players.values():
            for discard in player.discards:
                if discard.called_by is None:
                    counts[discard.tile] += 1
            for meld in player.melds:
                if meld.meld_type is not MeldType.CONCEALED_GANG:
                    counts[meld.tile] += meld.tile_count
        return counts

    def _validate(self) -> None:
        state = self.full_state
        counts = [0] * TILE_KIND_COUNT
        for player in state.players.values():
            for tile, amount in enumerate(player.hand):
                counts[tile] += amount
            for discard in player.discards:
                if discard.called_by is None:
                    counts[discard.tile] += 1
            for meld in player.melds:
                counts[meld.tile] += meld.tile_count
        for tile in state.wall[state.wall_index:]:
            counts[tile] += 1
        if counts != [COPIES_PER_TILE] * TILE_KIND_COUNT:
            raise RuntimeError("simulator tile conservation failed")
