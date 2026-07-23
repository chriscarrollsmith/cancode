#!/usr/bin/env bash
set -euo pipefail

SERVER_IP="${SERVER_IP:-$(curl -4 -fsS https://ifconfig.me)}"
EMAIL="${LETSENCRYPT_EMAIL:-}"
WEBROOT=/var/www/certbot

mkdir -p "$WEBROOT"
install -m 644 /opt/soup-game/deploy/nginx-http-bootstrap.conf \
  /etc/nginx/sites-available/soup-game
ln -sfn /etc/nginx/sites-available/soup-game /etc/nginx/sites-enabled/soup-game
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

ARGS=(
  certonly
  --non-interactive
  --agree-tos
  --keep-until-expiring
  --preferred-challenges http
  --webroot
  --webroot-path "$WEBROOT"
  --ip-address "$SERVER_IP"
  --cert-name "$SERVER_IP"
  --required-profile shortlived
)

if [ -n "$EMAIL" ]; then
  ARGS+=(--email "$EMAIL")
else
  ARGS+=(--register-unsafely-without-email)
fi

certbot "${ARGS[@]}"

sed "s/__SERVER_IP__/${SERVER_IP}/g" /opt/soup-game/deploy/nginx.conf \
  >/etc/nginx/sites-available/soup-game
nginx -t
systemctl reload nginx

# Renew frequently; IP certs last ~6 days.
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat >/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'HOOK'
#!/usr/bin/env bash
systemctl reload nginx
HOOK
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

# Certbot snap ships a timer; ensure it is enabled.
systemctl enable --now snap.certbot.renew.timer 2>/dev/null || true

echo "HTTPS ready at https://${SERVER_IP}/"
