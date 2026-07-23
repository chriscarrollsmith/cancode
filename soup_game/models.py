"""Shared typed models for Soup Game state and API payloads."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Phase(StrEnum):
    LOBBY = "lobby"
    ANSWERING = "answering"
    VOTING = "voting"
    RESULTS = "results"


class Player(BaseModel):
    id: str
    name: str
    connected: bool = True
    score: int = 0


class RoomState(BaseModel):
    phase: Phase = Phase.LOBBY
    round_number: int = 0
    players: dict[str, Player] = Field(default_factory=dict)
    active_player_ids: list[str] = Field(default_factory=list)
    prompt_noun: str = ""
    prompt_text: str = ""
    answers: dict[str, str] = Field(default_factory=dict)
    votes: dict[str, str] = Field(default_factory=dict)
    phase_ends_at: float | None = None
    winner_id: str | None = None
    winner_ids: list[str] = Field(default_factory=list)
    status_message: str = "Waiting for players…"


class JoinRequest(BaseModel):
    name: str = Field(min_length=1, max_length=24)


class JoinResponse(BaseModel):
    player_id: str
    name: str


class AnswerRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200)


class VoteRequest(BaseModel):
    target_player_id: str


class ClientEvent(BaseModel):
    type: Literal["answer", "vote", "ping"]
    text: str | None = None
    target_player_id: str | None = None


class PublicPlayer(BaseModel):
    id: str
    name: str
    connected: bool
    score: int
    is_active: bool


class PublicAnswer(BaseModel):
    player_id: str
    player_name: str
    text: str
    vote_count: int | None = None


class PublicState(BaseModel):
    phase: Phase
    round_number: int
    prompt_text: str
    prompt_noun: str
    phase_ends_at: float | None
    status_message: str
    players: list[PublicPlayer]
    active_player_ids: list[str]
    answers: list[PublicAnswer]
    my_player_id: str | None
    my_role: Literal["spectator", "player", "voter"]
    has_submitted_answer: bool
    has_voted: bool
    winner_ids: list[str]
    winner_names: list[str]
    connected_count: int
    min_players: int
