"""Core Soup Game rules and phase transitions."""

from __future__ import annotations

import random
import time
import uuid
from typing import Literal

from soup_game import config
from soup_game.models import (
    Phase,
    Player,
    PublicAnswer,
    PublicPlayer,
    PublicState,
    RoomState,
)
from soup_game.prompts import build_prompt, random_soup_noun
from soup_game.store import RoomStore


def now() -> float:
    return time.time()


def connected_players(room: RoomState) -> list[Player]:
    return [p for p in room.players.values() if p.connected]


def sanitize_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    if not cleaned:
        return "Guest"
    return cleaned[:24]


class GameService:
    def __init__(self, store: RoomStore) -> None:
        self.store = store

    async def join(self, name: str, player_id: str | None = None) -> Player:
        async with self.store.lock():
            room = await self.store.get_room()
            pid = player_id or str(uuid.uuid4())
            display = sanitize_name(name)
            existing = room.players.get(pid)
            if existing is not None:
                existing.name = display
                player = existing
            else:
                # Presence is owned by the WebSocket connection lifecycle.
                player = Player(id=pid, name=display, connected=False, score=0)
                room.players[pid] = player
            if room.phase == Phase.LOBBY:
                room.status_message = self._lobby_message(room)
            await self.store.save_and_publish(room)
            return player

    async def set_connected(self, player_id: str, connected: bool) -> None:
        async with self.store.lock():
            room = await self.store.get_room()
            player = room.players.get(player_id)
            if player is None:
                return
            player.connected = connected
            if room.phase == Phase.LOBBY:
                room.status_message = self._lobby_message(room)
            await self.store.save_and_publish(room)

    async def submit_answer(self, player_id: str, text: str) -> RoomState:
        async with self.store.lock():
            room = await self.store.get_room()
            if room.phase != Phase.ANSWERING:
                return room
            if player_id not in room.active_player_ids:
                return room
            cleaned = " ".join(text.strip().split())
            if not cleaned:
                return room
            room.answers[player_id] = cleaned[:200]
            if self._all_answers_in(room):
                self._begin_voting(room)
            await self.store.save_and_publish(room)
            return room

    async def cast_vote(self, voter_id: str, target_player_id: str) -> RoomState:
        async with self.store.lock():
            room = await self.store.get_room()
            if room.phase != Phase.VOTING:
                return room
            if voter_id in room.active_player_ids:
                return room
            if voter_id not in room.players or not room.players[voter_id].connected:
                return room
            if target_player_id not in room.answers:
                return room
            room.votes[voter_id] = target_player_id
            if self._all_votes_in(room):
                self._begin_results(room)
            await self.store.save_and_publish(room)
            return room

    async def tick(self) -> None:
        async with self.store.lock():
            room = await self.store.get_room()
            changed = self._advance(room)
            if changed:
                await self.store.save_and_publish(room)

    def to_public(self, room: RoomState, viewer_id: str | None) -> PublicState:
        role = self._role(room, viewer_id)
        show_answer_text = room.phase in {Phase.VOTING, Phase.RESULTS}
        show_vote_counts = room.phase == Phase.RESULTS

        answers: list[PublicAnswer] = []
        if show_answer_text:
            vote_counts = self._vote_counts(room)
            for pid, text in room.answers.items():
                player = room.players.get(pid)
                answers.append(
                    PublicAnswer(
                        player_id=pid,
                        player_name=player.name if player else "Unknown",
                        text=text,
                        vote_count=(
                            vote_counts.get(pid, 0) if show_vote_counts else None
                        ),
                    )
                )
            random.Random(room.round_number).shuffle(answers)
        elif room.phase == Phase.ANSWERING and viewer_id in room.answers:
            player = room.players.get(viewer_id)
            answers.append(
                PublicAnswer(
                    player_id=viewer_id,
                    player_name=player.name if player else "You",
                    text=room.answers[viewer_id],
                    vote_count=None,
                )
            )

        players = [
            PublicPlayer(
                id=p.id,
                name=p.name,
                connected=p.connected,
                score=p.score,
                is_active=p.id in room.active_player_ids,
            )
            for p in sorted(room.players.values(), key=lambda x: x.name.lower())
        ]

        winner_names = [
            room.players[wid].name
            for wid in room.winner_ids
            if wid in room.players
        ]

        return PublicState(
            phase=room.phase,
            round_number=room.round_number,
            prompt_text=room.prompt_text,
            prompt_noun=room.prompt_noun,
            phase_ends_at=room.phase_ends_at,
            status_message=room.status_message,
            players=players,
            active_player_ids=list(room.active_player_ids),
            answers=answers,
            my_player_id=viewer_id,
            my_role=role,
            has_submitted_answer=bool(
                viewer_id and viewer_id in room.answers
            ),
            has_voted=bool(viewer_id and viewer_id in room.votes),
            winner_ids=list(room.winner_ids),
            winner_names=winner_names,
            connected_count=len(connected_players(room)),
            min_players=config.MIN_PLAYERS,
        )

    def _advance(self, room: RoomState) -> bool:
        t = now()
        if room.phase == Phase.LOBBY:
            if len(connected_players(room)) >= config.MIN_PLAYERS:
                if room.phase_ends_at is None:
                    room.phase_ends_at = t + config.LOBBY_START_DELAY_SECONDS
                    room.status_message = "Enough players! Round starting…"
                    return True
                if t >= room.phase_ends_at:
                    return self._start_round(room)
            elif room.phase_ends_at is not None:
                room.phase_ends_at = None
                room.status_message = self._lobby_message(room)
                return True
            return False

        if room.phase_ends_at is not None and t >= room.phase_ends_at:
            if room.phase == Phase.ANSWERING:
                if len(room.answers) >= 1:
                    self._begin_voting(room)
                else:
                    room.status_message = "No answers this round. Trying again…"
                    self._reset_to_lobby(room, delay=2.0)
                return True
            if room.phase == Phase.VOTING:
                self._begin_results(room)
                return True
            if room.phase == Phase.RESULTS:
                self._reset_to_lobby(room, delay=config.LOBBY_START_DELAY_SECONDS)
                return True
        return False

    def _start_round(self, room: RoomState) -> bool:
        pool = connected_players(room)
        if len(pool) < config.MIN_PLAYERS:
            self._reset_to_lobby(room, delay=None)
            return True

        count = min(config.ACTIVE_PLAYERS_PER_ROUND, len(pool))
        chosen = random.sample(pool, k=count)
        noun = random_soup_noun()

        room.phase = Phase.ANSWERING
        room.round_number += 1
        room.active_player_ids = [p.id for p in chosen]
        room.prompt_noun = noun
        room.prompt_text = build_prompt(noun)
        room.answers = {}
        room.votes = {}
        room.winner_id = None
        room.winner_ids = []
        room.phase_ends_at = now() + config.ANSWER_SECONDS
        names = " & ".join(p.name for p in chosen)
        room.status_message = f"{names} — write your best punchline!"
        return True

    def _begin_voting(self, room: RoomState) -> None:
        if not room.answers:
            room.status_message = "No answers this round. Trying again…"
            self._reset_to_lobby(room, delay=2.0)
            return
        room.phase = Phase.VOTING
        room.votes = {}
        room.phase_ends_at = now() + config.VOTE_SECONDS
        room.status_message = "Vote for the best answer!"

    def _begin_results(self, room: RoomState) -> None:
        counts = self._vote_counts(room)
        if not counts:
            # No votes: pick randomly among answers, or declare no winner.
            if room.answers:
                winner = random.choice(list(room.answers.keys()))
                room.winner_ids = [winner]
            else:
                room.winner_ids = []
        else:
            best = max(counts.values())
            room.winner_ids = [pid for pid, c in counts.items() if c == best]

        for wid in room.winner_ids:
            player = room.players.get(wid)
            if player is not None:
                player.score += 1

        room.winner_id = room.winner_ids[0] if len(room.winner_ids) == 1 else None
        room.phase = Phase.RESULTS
        room.phase_ends_at = now() + config.RESULTS_SECONDS
        if not room.winner_ids:
            room.status_message = "No winner this round."
        elif len(room.winner_ids) == 1:
            name = room.players[room.winner_ids[0]].name
            room.status_message = f"{name} wins the round!"
        else:
            names = " & ".join(
                room.players[wid].name for wid in room.winner_ids if wid in room.players
            )
            room.status_message = f"Tie! {names} share the crown."

    def _reset_to_lobby(self, room: RoomState, delay: float | None) -> None:
        room.phase = Phase.LOBBY
        room.active_player_ids = []
        room.prompt_noun = ""
        room.prompt_text = ""
        room.answers = {}
        room.votes = {}
        room.winner_id = None
        room.winner_ids = []
        if delay is None:
            room.phase_ends_at = None
        else:
            room.phase_ends_at = now() + delay
        room.status_message = self._lobby_message(room)

    def _lobby_message(self, room: RoomState) -> str:
        count = len(connected_players(room))
        need = config.MIN_PLAYERS
        if count < need:
            return f"Waiting for players… {count}/{need} connected"
        return "Enough players! Round starting…"

    def _all_answers_in(self, room: RoomState) -> bool:
        return all(pid in room.answers for pid in room.active_player_ids)

    def _all_votes_in(self, room: RoomState) -> bool:
        voters = [
            p.id
            for p in connected_players(room)
            if p.id not in room.active_player_ids
        ]
        if not voters:
            return True
        return all(vid in room.votes for vid in voters)

    def _vote_counts(self, room: RoomState) -> dict[str, int]:
        counts: dict[str, int] = {pid: 0 for pid in room.answers}
        for target in room.votes.values():
            if target in counts:
                counts[target] += 1
        return counts

    def _role(
        self, room: RoomState, viewer_id: str | None
    ) -> Literal["spectator", "player", "voter"]:
        if viewer_id is None or viewer_id not in room.players:
            return "spectator"
        if room.phase == Phase.ANSWERING and viewer_id in room.active_player_ids:
            return "player"
        if room.phase == Phase.VOTING and viewer_id not in room.active_player_ids:
            return "voter"
        if viewer_id in room.active_player_ids:
            return "player"
        return "spectator"
