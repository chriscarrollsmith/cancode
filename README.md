# Soup Game

**Live:** https://87.99.128.58/

A tiny multiplayer party game in one shared room.

**Prompt:** *Waiter, there's a {random noun} in my soup!*  
Two players get 30 seconds to write a punchline. Everyone else votes. Winner gets crowned, then a new random pair is promoted for the next round.

## Stack

- FastAPI + Jinja2 + WebSockets
- Redis for shared room state
- UV for packaging
- Ruff + Ty for linting and type checking
- Wonder Words for random nouns

## Local development

```bash
uv sync
docker run --rm -p 6379:6379 redis:7   # or any local Redis
export REDIS_URL=redis://127.0.0.1:6379/0
uv run uvicorn soup_game.main:app --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). You need at least 3 connected players to start a round.

## Checks

```bash
uv run ruff check .
uv run ty check
```

## Deploy

The Hetzner host uses Redis, systemd, and nginx. From a machine with SSH access:

```bash
rsync -az --delete --exclude .venv --exclude .git ./ root@SERVER:/opt/soup-game/
ssh root@SERVER 'bash /opt/soup-game/deploy/setup-server.sh'
```

## HTTPS (IP certificate)

Soup Game uses a Let's Encrypt short-lived certificate for the server IP
(~6 day lifetime, auto-renewed by Certbot):

```bash
SERVER_IP=87.99.128.58 LETSENCRYPT_EMAIL=you@example.com bash deploy/issue-ip-cert.sh
```
