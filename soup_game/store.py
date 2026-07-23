"""Redis-backed persistence and pub/sub for the shared Soup Game room."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypeVar

from redis.asyncio import Redis

from soup_game import config
from soup_game.models import RoomState

T = TypeVar("T")


class RoomStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_room(self) -> RoomState:
        raw = await self._redis.get(config.ROOM_KEY)
        if raw is None:
            return RoomState()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return RoomState.model_validate_json(raw)

    async def save_room(self, room: RoomState) -> None:
        await self._redis.set(config.ROOM_KEY, room.model_dump_json())

    async def publish(self, room: RoomState) -> None:
        await self._redis.publish(config.BROADCAST_CHANNEL, room.model_dump_json())

    async def save_and_publish(self, room: RoomState) -> None:
        await self.save_room(room)
        await self.publish(room)

    @asynccontextmanager
    async def lock(self, timeout: float = 5.0) -> AsyncIterator[None]:
        token = f"{asyncio.get_running_loop().time()}"
        acquired = False
        deadline = asyncio.get_running_loop().time() + timeout
        try:
            while asyncio.get_running_loop().time() < deadline:
                ok = await self._redis.set(
                    config.ROOM_LOCK_KEY,
                    token,
                    nx=True,
                    px=int(timeout * 1000),
                )
                if ok:
                    acquired = True
                    break
                await asyncio.sleep(0.02)
            if not acquired:
                raise TimeoutError("Could not acquire room lock")
            yield
        finally:
            if acquired:
                current = await self._redis.get(config.ROOM_LOCK_KEY)
                if current is not None:
                    current_s = (
                        current.decode("utf-8")
                        if isinstance(current, bytes)
                        else str(current)
                    )
                    if current_s == token:
                        await self._redis.delete(config.ROOM_LOCK_KEY)

    async def subscribe(self) -> AsyncIterator[RoomState]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(config.BROADCAST_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message is None:
                    continue
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if data is None:
                    continue
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                if not isinstance(data, str):
                    continue
                yield RoomState.model_validate_json(data)
        finally:
            await pubsub.unsubscribe(config.BROADCAST_CHANNEL)
            await pubsub.aclose()
