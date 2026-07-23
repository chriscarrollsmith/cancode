#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/soup-game
REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-cursor/soup-game-5d17}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl git nginx redis-server python3 python3-venv

systemctl enable --now redis-server

if [ ! -e /usr/local/bin/uv ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  install -m 755 /root/.local/bin/uv /usr/local/bin/uv
fi

mkdir -p "$APP_DIR"
if [ -n "$REPO_URL" ]; then
  if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" fetch origin
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" reset --hard "origin/$BRANCH"
  else
    rm -rf "$APP_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
  fi
fi

cd "$APP_DIR"
uv sync --frozen || uv sync
chown -R www-data:www-data "$APP_DIR"

install -m 644 "$APP_DIR/deploy/soup-game.service" /etc/systemd/system/soup-game.service
install -m 644 "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/soup-game
ln -sfn /etc/nginx/sites-available/soup-game /etc/nginx/sites-enabled/soup-game
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable soup-game
systemctl restart soup-game
nginx -t
systemctl reload nginx

echo "Soup Game is live."
