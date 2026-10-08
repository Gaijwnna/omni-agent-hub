#!/usr/bin/env bash
# One-shot setup for an Oracle Cloud (OCI) VM. Run ON the server, from a clone
# of this repository:
#
#   sudo bash deploy/oracle-setup.sh
#
# Safe to re-run: it keeps an existing .env and only rebuilds/restarts containers.
# Secrets are generated on the server and never leave it.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE="$REPO_DIR/Omni-Agent-Hub-Server-Release-Candidate.zip"
INSTALL_DIR="${INSTALL_DIR:-/opt/omni-agent-hub}"
APP_DIR="$INSTALL_DIR/launch"

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo bash $0"; exit 1; }
[ -f "$ARCHIVE" ] || { echo "Archive not found at $ARCHIVE"; exit 1; }

. /etc/os-release
case "$ID" in
  ubuntu|debian) PKG=apt ;;
  ol|rhel|centos|rocky|almalinux|fedora) PKG=dnf ;;
  *) echo "Unsupported OS: $ID (use Ubuntu 22.04/24.04)"; exit 1 ;;
esac

sed_escape() { printf '%s' "$1" | sed -e 's/[|&\\]/\\&/g'; }

# ---- Questions -------------------------------------------------------------
read -rp "Domain pointing at this server (blank = test by IP only, no HTTPS): " DOMAIN
read -rp "Operator / business name shown on legal pages: " CONTROLLER_NAME
read -rp "Contact email (also used for Let's Encrypt): " CONTACT_EMAIL

# ---- Packages --------------------------------------------------------------
say "Installing Docker, nginx, certbot"
if [ "$PKG" = apt ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y ca-certificates curl unzip openssl nginx certbot python3-certbot-nginx iptables-persistent
  command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh
else
  dnf install -y dnf-plugins-core curl unzip openssl nginx
  dnf install -y oracle-epel-release-el"${VERSION_ID%%.*}" 2>/dev/null || dnf install -y epel-release || true
  dnf install -y certbot python3-certbot-nginx || warn "certbot not installed; HTTPS step may fail"
  if ! command -v docker >/dev/null; then
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  fi
fi
systemctl enable --now docker nginx

# ---- Host firewall (OCI images block 80/443 by default) --------------------
say "Opening ports 80 and 443 in the host firewall"
if command -v firewall-cmd >/dev/null && systemctl is-active --quiet firewalld; then
  firewall-cmd --permanent --add-service=http --add-service=https && firewall-cmd --reload
else
  for p in 80 443; do
    iptables -C INPUT -p tcp --dport "$p" -m state --state NEW -j ACCEPT 2>/dev/null && continue
    # Insert above OCI's catch-all REJECT rule, if present.
    pos="$(iptables -L INPUT --line-numbers -n | awk '$2=="REJECT"{print $1; exit}')"
    iptables -I INPUT "${pos:-1}" -p tcp --dport "$p" -m state --state NEW -j ACCEPT
  done
  command -v netfilter-persistent >/dev/null && netfilter-persistent save
fi

# ---- Code ------------------------------------------------------------------
say "Extracting release into $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
EXISTING_ENV=""
[ -f "$APP_DIR/.env" ] && EXISTING_ENV="$(cat "$APP_DIR/.env")"
unzip -oq "$ARCHIVE" -d "$INSTALL_DIR"

# ---- Secrets / .env --------------------------------------------------------
if [ -n "$EXISTING_ENV" ]; then
  say "Keeping existing .env"
  printf '%s\n' "$EXISTING_ENV" > "$APP_DIR/.env"
else
  say "Generating secrets in $APP_DIR/.env (stays on this server)"
  if [ -n "$DOMAIN" ]; then PUBLIC_URL="https://$DOMAIN"; else
    IP="$(curl -fsS https://ifconfig.me || hostname -I | awk '{print $1}')"; PUBLIC_URL="http://$IP"; fi
  sed \
    -e "s|^PUBLIC_URL=.*|PUBLIC_URL=$PUBLIC_URL|" \
    -e "s|^APP_SECRET=.*|APP_SECRET=$(openssl rand -base64 48 | tr -d '\n/+=')|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" \
    -e "s|^BENCHMARK_SIGNING_KEY=.*|BENCHMARK_SIGNING_KEY=$(openssl rand -base64 32 | tr -d '\n')|" \
    -e "s|^CONTROLLER_NAME=.*|CONTROLLER_NAME=$(sed_escape "$CONTROLLER_NAME")|" \
    -e "s|^CONTACT_EMAIL=.*|CONTACT_EMAIL=$(sed_escape "$CONTACT_EMAIL")|" \
    "$APP_DIR/.env.example" > "$APP_DIR/.env"
fi
chmod 600 "$APP_DIR/.env"

# ---- Containers ------------------------------------------------------------
say "Building and starting containers (first build takes several minutes)"
cd "$APP_DIR"
docker compose up --build -d

# ---- nginx -----------------------------------------------------------------
say "Configuring nginx reverse proxy"
SERVER_NAME="${DOMAIN:-_}"
cat > /tmp/omni-site.conf <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_NAME;
$(sed 's/^/    /' "$APP_DIR/ops/nginx.conf")
}
EOF
if [ -d /etc/nginx/sites-available ]; then
  mv /tmp/omni-site.conf /etc/nginx/sites-available/omni-agent-hub
  ln -sf /etc/nginx/sites-available/omni-agent-hub /etc/nginx/sites-enabled/omni-agent-hub
  rm -f /etc/nginx/sites-enabled/default
else
  mv /tmp/omni-site.conf /etc/nginx/conf.d/omni-agent-hub.conf
  command -v setsebool >/dev/null && setsebool -P httpd_can_network_connect 1 || true
fi
nginx -t && systemctl reload nginx

if [ -n "$DOMAIN" ]; then
  say "Requesting HTTPS certificate for $DOMAIN"
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$CONTACT_EMAIL" --redirect \
    || warn "Certificate failed. Check DNS points here and OCI ingress allows 80/443, then: sudo certbot --nginx -d $DOMAIN"
fi

# ---- Check -----------------------------------------------------------------
say "Waiting for the app to respond"
for _ in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8000/api/v1/status >/dev/null 2>&1 && break; sleep 3
done
if curl -fsS http://127.0.0.1:8000/api/v1/status; then
  echo; say "Running. Open ${DOMAIN:+https://$DOMAIN}${DOMAIN:-http://<server-ip>}"
else
  warn "App not responding yet. Inspect with: cd $APP_DIR && docker compose ps && docker compose logs --tail=80"
fi
docker compose ps
warn "Renderer uses Chromium's sandbox. If scans fail, check: docker compose logs renderer (do NOT add --no-sandbox)."
warn "Still in ENVIRONMENT=development. Switch to production in $APP_DIR/.env only after the checks in launch/docs/LAUNCH_STATUS.md."
