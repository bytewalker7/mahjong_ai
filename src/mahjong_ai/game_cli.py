"""Interactive command-line recorder for the event-sourced game state."""

from __future__ import annotations

import shlex
from collections.abc import Callable

from .analysis import analyze_discards, analyze_hand, format_tiles
from .meld import MeldType
from .state import (
    AdvanceTurn,
    CallExposedGang,
    CallPeng,
    DeclareAddedGang,
    DeclareConcealedGang,
    DeclareWin,
    DiscardTile,
    DrawOwnTile,
    GameState,
    HiddenDraw,
    PlayerPosition,
    SetOwnInitialHand,
    StartRound,
    apply_event,
    new_game,
    undo_last_event,
)
from .tiles import TileError, code_to_tile, parse_tiles, tile_to_code


_POSITIONS = {
    "self": PlayerPosition.SELF,
    "left": PlayerPosition.LEFT,
    "opposite": PlayerPosition.OPPOSITE,
    "right": PlayerPosition.RIGHT,
    "s": PlayerPosition.SELF,
    "l": PlayerPosition.LEFT,
    "o": PlayerPosition.OPPOSITE,
    "r": PlayerPosition.RIGHT,
}

HELP = """Commands:
  start <dealer>                         Start a round (self/left/opposite/right)
  hand <tile ...>                        Set SELF's initial hand
  draw <tile>                            Record SELF drawing a known tile
  hidden-draw <player>                   Record another player drawing a hidden tile
  discard <player> <tile>                Record a discard
  peng <player> <from-player> <tile>     Record a peng call on the last discard
  exposed-gang <player> <from> <tile>    Record an exposed gang on the last discard
  concealed-gang <player> <tile>         Record a concealed gang
  added-gang <player> <tile>             Upgrade that player's existing peng
  win <player>                           Record a win and finish the round
  next <player>                          Pass an uncalled discard to the next player
  undo                                   Undo the most recent event
  status                                 Show public state and SELF's hand
  analyze                                Analyze SELF's hand when it is SELF's turn
  help                                   Show this help
  quit | exit                            Leave the recorder"""


class GameCommandProcessor:
    """Parse one REPL line at a time while retaining one :class:`GameState`."""

    def __init__(self) -> None:
        self.state = new_game()

    def execute(self, line: str) -> str | None:
        """Execute one command and return display text, or ``None`` to exit."""
        parts = shlex.split(line)
        if not parts:
            return ""
        command = parts[0].lower()
        arguments = parts[1:]
        if command in {"quit", "exit"}:
            return None
        if command == "help":
            return HELP
        if command == "status":
            return self._format_status()
        if command == "analyze":
            return self._analyze()
        if command == "undo":
            self.state = undo_last_event(self.state)
            return "Undone.\n" + self._format_status()

        event = self._parse_event(command, arguments)
        self.state = apply_event(self.state, event)
        return "OK.\n" + self._format_status()

    def _parse_event(self, command: str, args: list[str]) -> object:
        if command == "start":
            self._exact(args, 1, "start <dealer>")
            return StartRound(self._position(args[0]))
        if command == "hand":
            if not args:
                raise ValueError("usage: hand <tile ...>")
            return SetOwnInitialHand(tuple(parse_tiles(" ".join(args))))
        if command == "draw":
            self._exact(args, 1, "draw <tile>")
            return DrawOwnTile(self._tile(args[0]))
        if command == "hidden-draw":
            self._exact(args, 1, "hidden-draw <player>")
            player = self._position(args[0])
            if player is PlayerPosition.SELF:
                raise ValueError("use draw <tile> for SELF")
            return HiddenDraw(player)
        if command == "discard":
            self._exact(args, 2, "discard <player> <tile>")
            return DiscardTile(self._position(args[0]), self._tile(args[1]))
        if command == "peng":
            self._exact(args, 3, "peng <player> <from-player> <tile>")
            return CallPeng(self._position(args[0]), self._tile(args[2]), self._position(args[1]))
        if command == "exposed-gang":
            self._exact(args, 3, "exposed-gang <player> <from-player> <tile>")
            return CallExposedGang(self._position(args[0]), self._tile(args[2]), self._position(args[1]))
        if command == "concealed-gang":
            self._exact(args, 2, "concealed-gang <player> <tile>")
            return DeclareConcealedGang(self._position(args[0]), self._tile(args[1]))
        if command == "added-gang":
            self._exact(args, 2, "added-gang <player> <tile>")
            return DeclareAddedGang(self._position(args[0]), self._tile(args[1]))
        if command == "win":
            self._exact(args, 1, "win <player>")
            return DeclareWin(self._position(args[0]))
        if command == "next":
            self._exact(args, 1, "next <player>")
            return AdvanceTurn(self._position(args[0]))
        raise ValueError(f"unknown command {command!r}; type help for commands")

    @staticmethod
    def _exact(args: list[str], count: int, usage: str) -> None:
        if len(args) != count:
            raise ValueError(f"usage: {usage}")

    @staticmethod
    def _tile(text: str) -> int:
        return tile_to_code(text)

    @staticmethod
    def _position(text: str) -> PlayerPosition:
        try:
            return _POSITIONS[text.lower()]
        except KeyError as error:
            raise ValueError("player must be self, left, opposite, or right") from error

    def _format_status(self) -> str:
        state = self.state
        lines = [
            f"Current: {state.current_player.name}; dealer: {state.dealer.name}; wall: {state.wall_remaining}",
            "SELF hand: " + " ".join(code_to_tile(tile) for tile, count in enumerate(state.own_hand) for _ in range(count)),
        ]
        for position in PlayerPosition:
            player = state.players[position]
            discards = " ".join(
                code_to_tile(discard.tile) + ("*" if discard.called_by is not None else "")
                for discard in player.discards
            ) or "-"
            melds = " ".join(
                f"{meld.meld_type.value}:{code_to_tile(meld.tile)}" for meld in player.melds
            ) or "-"
            lines.append(f"{position.name}: concealed={player.concealed_tile_count}; discards={discards}; melds={melds}")
        if state.last_discard is not None:
            lines.append(f"Last discard: {state.last_discard.player.name} {code_to_tile(state.last_discard.tile)}")
        return "\n".join(lines)

    def _analyze(self) -> str:
        state = self.state
        if state.round_finished:
            raise ValueError("round is finished")
        if state.current_player is not PlayerPosition.SELF:
            raise ValueError("analysis is only available when current player is SELF")
        own_melds = state.players[PlayerPosition.SELF].melds
        known_unavailable = state.visible_counts.copy()
        # Concealed gangs are not public, but their tiles are still unavailable
        # to SELF and must be excluded from the theoretical remaining count.
        for meld in own_melds:
            if meld.meld_type is MeldType.CONCEALED_GANG:
                known_unavailable[meld.tile] += meld.tile_count
        result = analyze_hand(state.own_hand, known_unavailable, fixed_melds=len(own_melds))
        lines = [
            f"Shanten: {result.shanten}",
            f"Waits: {format_tiles(result.winning_tiles)}",
            f"Effective tiles: {format_tiles(result.effective_tiles)}",
        ]
        if result.effective_tiles:
            remaining = ", ".join(f"{code_to_tile(tile)}={result.remaining_by_tile[tile]}" for tile in result.effective_tiles)
            lines.append(f"Effective remaining: {remaining}")
        if sum(state.own_hand) % 3 == 2:
            candidates = analyze_discards(state.own_hand, known_unavailable, fixed_melds=len(own_melds))
            if candidates:
                lines.append(f"Recommended discard: {code_to_tile(candidates[0].discard)}")
                lines.append("Discard candidates:")
                for candidate in candidates:
                    lines.append(
                        f"  {code_to_tile(candidate.discard)}: shanten={candidate.analysis.shanten}, "
                        f"effective={format_tiles(candidate.analysis.effective_tiles)}, "
                        f"remaining={candidate.analysis.total_effective_tiles}"
                    )
        else:
            lines.append("Discard recommendation requires a post-draw hand.")
        return "\n".join(lines)


def main(input_fn: Callable[[str], str] = input, output: Callable[[str], None] = print) -> None:
    """Run the interactive game recorder."""
    processor = GameCommandProcessor()
    output("Mahjong game recorder. Type 'help' for commands.")
    while True:
        try:
            line = input_fn("mahjong> ")
        except (EOFError, KeyboardInterrupt):
            output("\nBye.")
            return
        try:
            result = processor.execute(line)
        except (TileError, ValueError) as error:
            output(f"Error: {error}")
            continue
        if result is None:
            output("Bye.")
            return
        if result:
            output(result)
