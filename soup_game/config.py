"""Runtime configuration for Soup Game."""

from __future__ import annotations

import os


def redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")


ANSWER_SECONDS: float = 30.0
VOTE_SECONDS: float = 30.0
RESULTS_SECONDS: float = 8.0
LOBBY_START_DELAY_SECONDS: float = 3.0
MIN_PLAYERS: int = 3
ACTIVE_PLAYERS_PER_ROUND: int = 2
ROOM_KEY: str = "soup:room"
ROOM_LOCK_KEY: str = "soup:lock"
BROADCAST_CHANNEL: str = "soup:broadcast"
TICK_INTERVAL_SECONDS: float = 0.25
