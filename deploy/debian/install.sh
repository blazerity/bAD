#!/usr/bin/env bash
# Однострочный установщик bAD для Debian 12
# Использование (сразу HTTPS):
#   BAD_DOMAIN=bad.example.com BAD_TLS_CERT=/path/fullchain.pem BAD_TLS_KEY=/path/privkey.pem \
#     sudo -E bash install.sh
# HTTP bootstrap (сертификат позже из UI /settings/tls):
#   BAD_DOMAIN=bad.example.com sudo -E bash install.sh
# Или:
#   curl -fsSL https://<distribution-host>/bad/install.sh | sudo bash
set -euo pipefail

BAD_VERSION="${BAD_VERSION:-0.12.0}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "error: must run as root" >&2
  exit 1
fi

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" != "debian" ]] || [[ "${VERSION_ID:-}" != "12" ]]; then
    echo "warning: designed for Debian 12 (got ${PRETTY_NAME:-unknown}); continuing anyway" >&2
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Checkout репозитория или пакетный tarball: server/ на два уровня выше deploy/debian/.
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

prompt() {
  local var="$1" msg="$2"
  if [[ -z "${!var:-}" ]]; then
    read -r -p "${msg}: " "$var"
    export "$var"
  fi
}

prompt BAD_DOMAIN "Public DNS name for this bAD server (cert SAN/CN)"

# TLS optional (0.11): empty = HTTP bootstrap until UI upload at /settings/tls
if [[ -z "${BAD_TLS_CERT:-}" && -z "${BAD_TLS_KEY:-}" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "TLS fullchain path [Enter = upload later via /settings/tls]: " BAD_TLS_CERT || true
    export BAD_TLS_CERT="${BAD_TLS_CERT:-}"
  fi
fi

HAS_TLS=0
if [[ -n "${BAD_TLS_CERT:-}" || -n "${BAD_TLS_KEY:-}" ]]; then
  prompt BAD_TLS_CERT "Absolute path to TLS certificate (fullchain)"
  prompt BAD_TLS_KEY "Absolute path to TLS private key"
  if [[ ! -f "${BAD_TLS_CERT}" ]]; then
    echo "error: cert not found: ${BAD_TLS_CERT}" >&2
    exit 1
  fi
  if [[ ! -f "${BAD_TLS_KEY}" ]]; then
    echo "error: key not found: ${BAD_TLS_KEY}" >&2
    exit 1
  fi
  HAS_TLS=1
  if command -v openssl >/dev/null 2>&1; then
    if ! openssl x509 -in "${BAD_TLS_CERT}" -noout -text 2>/dev/null | grep -Eq "DNS:${BAD_DOMAIN}|CN\\s*=\\s*${BAD_DOMAIN}"; then
      echo "warning: certificate may not cover domain ${BAD_DOMAIN}; verify CN/SAN manually" >&2
    fi
  fi
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx sqlite3 ufw openssl ca-certificates curl acl

id -u bad >/dev/null 2>&1 || useradd --system --home /var/lib/bad --shell /usr/sbin/nologin bad

mkdir -p /opt/bad /var/lib/bad /var/lib/bad/agent-updates /etc/bad /etc/bad/tls/staging /var/log/bad
chown bad:bad /var/lib/bad /var/lib/bad/agent-updates /var/log/bad
chmod 750 /var/lib/bad /var/lib/bad/agent-updates /var/log/bad
chmod 750 /etc/bad
chown root:bad /etc/bad/tls
chmod 770 /etc/bad/tls
chown bad:bad /etc/bad/tls/staging
chmod 770 /etc/bad/tls/staging

# Cookie Secure follows X-Forwarded-Proto (no force 0/1 → no ~2s race after TLS apply).
COOKIE_SECURE=auto
if [[ "${HAS_TLS}" -eq 1 ]]; then
  # Симлинк клиентского cert/key в /etc/bad/tls (UI-upload заменит на реальные файлы)
  ln -sfn "${BAD_TLS_CERT}" /etc/bad/tls/fullchain.pem
  ln -sfn "${BAD_TLS_KEY}" /etc/bad/tls/privkey.pem
else
  rm -f /etc/bad/tls/fullchain.pem /etc/bad/tls/privkey.pem
fi

# Установить приложение в /opt/bad
mkdir -p /opt/bad/server
rm -rf /opt/bad/server/*
cp -a "${REPO_ROOT}/server/." /opt/bad/server/
rm -rf /opt/bad/server/.venv /opt/bad/server/data /opt/bad/server/.pytest_cache
find /opt/bad/server -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# Nginx templates + TLS apply helper for HTTP→HTTPS and UI reload
mkdir -p /opt/bad/deploy/debian/nginx
cp -a "${SCRIPT_DIR}/nginx/." /opt/bad/deploy/debian/nginx/
install -m 755 "${SCRIPT_DIR}/bad-apply-tls.sh" /usr/local/sbin/bad-apply-tls

cd /opt/bad
python3 -m venv .venv
.venv/bin/pip install -U pip wheel
.venv/bin/pip install -e ./server

# Master secrets outside SQLite (SEC-005): Fernet data_key + session cookie secret.
# Do not store these only in bad.db — a DB/backup copy would decrypt SMTP/LDAP and forge sessions.
umask 077
if [[ ! -f /etc/bad/data_key ]]; then
  /opt/bad/.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' > /etc/bad/data_key
  chown root:bad /etc/bad/data_key
  chmod 440 /etc/bad/data_key
fi
if [[ ! -f /etc/bad/session_secret ]]; then
  openssl rand -base64 48 | tr -d '\n' > /etc/bad/session_secret
  chown root:bad /etc/bad/session_secret
  chmod 440 /etc/bad/session_secret
fi

# Сгенерировать токены один раз, если site.env ещё нет
SITE_ENV=/etc/bad/site.env
if [[ ! -f "${SITE_ENV}" ]]; then
  ENROLLMENT_TOKEN="bad_en_$(openssl rand -base64 48 | tr -d '/+=' | head -c 48)"
  ADMIN_TOKEN="bad_ad_$(openssl rand -base64 48 | tr -d '/+=' | head -c 48)"
  umask 077
  cat > "${SITE_ENV}" <<EOF
BAD_DB_PATH=/var/lib/bad/bad.db
BAD_DOMAIN=${BAD_DOMAIN}
BAD_ENROLLMENT_TOKEN=${ENROLLMENT_TOKEN}
BAD_ADMIN_TOKEN=${ADMIN_TOKEN}
BAD_DATA_KEY_FILE=/etc/bad/data_key
BAD_SESSION_SECRET_FILE=/etc/bad/session_secret
BAD_COOKIE_SECURE=${COOKIE_SECURE}
BAD_GITHUB_REPO=${BAD_GITHUB_REPO:-blazerity/bAD}
BAD_AGENT_UPDATES_DIR=/var/lib/bad/agent-updates
BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS=${BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS:-3600}
BAD_AGENT_UPDATE_SYNC_ON_STARTUP=${BAD_AGENT_UPDATE_SYNC_ON_STARTUP:-true}
EOF
  chown root:bad "${SITE_ENV}"
  chmod 640 "${SITE_ENV}"
  PRINT_TOKENS=1
else
  # shellcheck disable=SC1090
  set -a; source "${SITE_ENV}"; set +a
  ENROLLMENT_TOKEN="${BAD_ENROLLMENT_TOKEN:-}"
  ADMIN_TOKEN="${BAD_ADMIN_TOKEN:-}"
  PRINT_TOKENS=0
  # Ensure secret file paths are present on upgrades.
  if ! grep -q '^BAD_DATA_KEY_FILE=' "${SITE_ENV}" 2>/dev/null; then
    printf '\nBAD_DATA_KEY_FILE=/etc/bad/data_key\nBAD_SESSION_SECRET_FILE=/etc/bad/session_secret\n' >> "${SITE_ENV}"
  fi
  if ! grep -q '^BAD_DOMAIN=' "${SITE_ENV}" 2>/dev/null; then
    printf '\nBAD_DOMAIN=%s\n' "${BAD_DOMAIN}" >> "${SITE_ENV}"
  fi
  if grep -q '^BAD_COOKIE_SECURE=' "${SITE_ENV}"; then
    sed -i "s/^BAD_COOKIE_SECURE=.*/BAD_COOKIE_SECURE=${COOKIE_SECURE}/" "${SITE_ENV}"
  else
    printf '\nBAD_COOKIE_SECURE=%s\n' "${COOKIE_SECURE}" >> "${SITE_ENV}"
  fi
fi

chown -R bad:bad /opt/bad
# Оставить venv/exec читаемыми для bad
chmod -R u+rwX,g+rX,o-rwx /opt/bad

# systemd: API + TLS apply path unit (NoNewPrivileges — apply только через path unit)
install -m 644 "${SCRIPT_DIR}/systemd/bad-api.service" /etc/systemd/system/bad-api.service
install -m 644 "${SCRIPT_DIR}/systemd/bad-tls-apply.service" /etc/systemd/system/bad-tls-apply.service
install -m 644 "${SCRIPT_DIR}/systemd/bad-tls-apply.path" /etc/systemd/system/bad-tls-apply.path
systemctl daemon-reload
systemctl enable --now bad-api.service
systemctl enable --now bad-tls-apply.path

# nginx via apply helper (HTTP-only until managed/symlink cert exists)
BAD_NGINX_TEMPLATE_DIR=/opt/bad/deploy/debian/nginx /usr/local/sbin/bad-apply-tls
systemctl enable --now nginx

# Базовые правила ufw
if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  if ufw status | grep -qi inactive; then
    echo "warning: enabling ufw with allow 22,80,443 — ensure SSH access is correct" >&2
    ufw --force enable || true
  fi
fi

# Дождаться health
for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8000/v1/health >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

SCHEME="https"
if [[ "${HAS_TLS}" -eq 0 ]]; then
  SCHEME="http"
fi

echo
echo "========================================"
echo " bAD server ${BAD_VERSION} installed"
echo "========================================"
echo " Version:          ${BAD_VERSION}"
echo " URL:              ${SCHEME}://${BAD_DOMAIN}/"
echo " Health:           ${SCHEME}://${BAD_DOMAIN}/v1/health"
echo " Web UI:           ${SCHEME}://${BAD_DOMAIN}/login"
if [[ "${HAS_TLS}" -eq 0 ]]; then
  echo " TLS:              HTTP bootstrap — upload cert at /settings/tls then use HTTPS"
else
  echo " TLS:              HTTPS (cert provided at install)"
fi
echo " Web login:        admin / admin  (change immediately on first login)"
echo " DB:               /var/lib/bad/bad.db"
echo " Secrets:          /etc/bad/data_key + /etc/bad/session_secret (not in DB backups)"
echo " Logs:             journalctl -u bad-api -f"
if [[ "${PRINT_TOKENS}" -eq 1 ]]; then
  echo " Enrollment token: ${ENROLLMENT_TOKEN}"
  echo " Admin API token:  ${ADMIN_TOKEN}  (Bearer for /v1/devices*; not for web login)"
  echo
  echo " Save these tokens now — they are in /etc/bad/site.env (mode 640, root:bad)."
else
  echo " Tokens:           already present in /etc/bad/site.env (not re-printed)"
fi
if [[ "${HAS_TLS}" -eq 1 ]]; then
  echo " MSI properties:   SERVERURL=https://${BAD_DOMAIN} ENROLLMENTTOKEN=<enrollment token>"
else
  echo " MSI properties:   install agents AFTER TLS upload (SERVERURL=https://${BAD_DOMAIN})"
fi
echo "========================================"
