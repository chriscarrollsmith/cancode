"""FastAPI application entrypoint for Soup Game."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import (
    Cookie,
    FastAPI,
    Form,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis.asyncio import Redis

from soup_game import config
from soup_game.game import GameService
from soup_game.models import ClientEvent
from soup_game.store import RoomStore

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class AppState:
    redis: Redis
    store: RoomStore
    game: GameService
    tick_task: asyncio.Task[None] | None = None


state = AppState()


async def _ticker() -> None:
    while True:
        with suppress(Exception):
            await state.game.tick()
        await asyncio.sleep(config.TICK_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    state.redis = Redis.from_url(config.redis_url(), decode_responses=False)
    state.store = RoomStore(state.redis)
    state.game = GameService(state.store)
    state.tick_task = asyncio.create_task(_ticker())
    try:
        yield
    finally:
        if state.tick_task is not None:
            state.tick_task.cancel()
            with suppress(asyncio.CancelledError):
                await state.tick_task
        await state.redis.aclose()


app = FastAPI(title="Soup Game", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    player_id: str | None = Cookie(default=None, alias="soup_player_id"),
) -> HTMLResponse:
    room = await state.store.get_room()
    public = state.game.to_public(room, player_id)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "state": public,
            "joined": player_id is not None and player_id in room.players,
        },
    )


@app.post("/join")
async def join(
    name: str = Form(...),
    player_id: str | None = Cookie(default=None, alias="soup_player_id"),
) -> RedirectResponse:
    player = await state.game.join(name=name, player_id=player_id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="soup_player_id",
        value=player.id,
        httponly=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@app.get("/api/state")
async def api_state(
    player_id: str | None = Cookie(default=None, alias="soup_player_id"),
) -> dict[str, object]:
    room = await state.store.get_room()
    return state.game.to_public(room, player_id).model_dump()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    player_id = websocket.cookies.get("soup_player_id")

    if player_id:
        await state.game.set_connected(player_id, True)

    room = await state.store.get_room()
    await websocket.send_json(state.game.to_public(room, player_id).model_dump())

    send_task = asyncio.create_task(_ws_forward(websocket, player_id))
    try:
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                continue
            event = ClientEvent.model_validate(payload)
            if event.type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if player_id is None:
                continue
            if event.type == "answer" and event.text is not None:
                await state.game.submit_answer(player_id, event.text)
            elif event.type == "vote" and event.target_player_id is not None:
                await state.game.cast_vote(player_id, event.target_player_id)
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
        with suppress(asyncio.CancelledError):
            await send_task
        if player_id:
            await state.game.set_connected(player_id, False)


async def _ws_forward(websocket: WebSocket, player_id: str | None) -> None:
    try:
        async for room in state.store.subscribe():
            public = state.game.to_public(room, player_id)
            await websocket.send_json(public.model_dump())
    except asyncio.CancelledError:
        raise
    except Exception:
        # Socket closed or Redis hiccup; exit forwarder.
        return


def run() -> None:
    import uvicorn

    uvicorn.run(
        "soup_game.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    run()
