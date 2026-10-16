#!/usr/bin/env bash
# Однострочный установщик bAD для Debian 12 (Postgres only)
# Использование (сразу HTTPS):
#   BAD_DOMAIN=bad.example.com BAD_TLS_CERT=/path/fullchain.pem BAD_TLS_KEY=/path/privkey.pem \
#     sudo -E bash install.sh
# HTTP bootstrap (сертификат позже из UI /settings/tls):
#   BAD_DOMAIN=bad.example.com sudo -E bash install.sh
# Или:
#   curl -fsSL https://<distribution-host>/bad/install.sh | sudo bash
set -euo pipefail

TOTAL_STEPS=6

step() {
  local n="$1"; shift
  echo
  echo "[${n}/${TOTAL_STEPS}] $*"
}

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
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# Корневой VERSION = semver **сервера** (не agent/VERSION).
if [[ -f "${REPO_ROOT}/VERSION" ]]; then
  BAD_VERSION="${BAD_VERSION:-$(head -1 "${REPO_ROOT}/VERSION" | tr -d '\r\n')}"
else
  BAD_VERSION="${BAD_VERSION:-1.2.0}"
fi
SITE_ENV=/etc/bad/site.env

prompt() {
  local var="$1" msg="$2"
  if [[ -z "${!var:-}" ]]; then
    read -r -p "${msg}: " "$var"
    export "$var"
  fi
}

prompt BAD_DOMAIN "Public DNS name for this bAD server (cert SAN/CN)"

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

# ========== [1/6] Пакеты ==========
step 1 "Пакеты"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  python3 python3-venv python3-pip nginx ufw openssl ca-certificates curl acl \
  postgresql postgresql-client

# ========== [2/6] Пользователь / каталоги / venv ==========
step 2 "Пользователь / каталоги / venv"
id -u bad >/dev/null 2>&1 || useradd --system --home /var/lib/bad --shell /usr/sbin/nologin bad

mkdir -p /opt/bad /var/lib/bad /var/lib/bad/agent-updates /var/lib/bad/backups \
  /var/lib/bad/server-releases /var/lib/bad/server-releases/slots \
  /var/lib/bad/server-releases/staging \
  /etc/bad /etc/bad/tls/staging /var/log/bad
chown bad:bad /var/lib/bad /var/lib/bad/agent-updates /var/lib/bad/backups /var/log/bad
chmod 750 /var/lib/bad /var/lib/bad/agent-updates /var/log/bad
chmod 700 /var/lib/bad/backups
chown root:bad /var/lib/bad/server-releases
chmod 770 /var/lib/bad/server-releases
chown bad:bad /var/lib/bad/server-releases/staging
chmod 770 /var/lib/bad/server-releases/staging
chown root:bad /var/lib/bad/server-releases/slots
chmod 750 /var/lib/bad/server-releases/slots
chmod 750 /etc/bad
chown root:bad /etc/bad/tls
chmod 770 /etc/bad/tls
chown bad:bad /etc/bad/tls/staging
chmod 770 /etc/bad/tls/staging

COOKIE_SECURE=auto
if [[ "${HAS_TLS}" -eq 1 ]]; then
  ln -sfn "${BAD_TLS_CERT}" /etc/bad/tls/fullchain.pem
  ln -sfn "${BAD_TLS_KEY}" /etc/bad/tls/privkey.pem
else
  rm -f /etc/bad/tls/fullchain.pem /etc/bad/tls/privkey.pem
fi

mkdir -p /opt/bad/server
rm -rf /opt/bad/server/*
cp -a "${REPO_ROOT}/server/." /opt/bad/server/
rm -rf /opt/bad/server/.venv /opt/bad/server/data /opt/bad/server/.pytest_cache
find /opt/bad/server -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# Server VERSION + agent/VERSION (#79) на диск для health / MSI dispatch
install -m 644 "${REPO_ROOT}/VERSION" /opt/bad/VERSION
mkdir -p /opt/bad/agent
if [[ -f "${REPO_ROOT}/agent/VERSION" ]]; then
  install -m 644 "${REPO_ROOT}/agent/VERSION" /opt/bad/agent/VERSION
fi

mkdir -p /opt/bad/deploy/debian/nginx
cp -a "${SCRIPT_DIR}/nginx/." /opt/bad/deploy/debian/nginx/
install -m 755 "${SCRIPT_DIR}/bad-apply-tls.sh" /usr/local/sbin/bad-apply-tls
install -m 755 "${SCRIPT_DIR}/bad-apply-server-update.sh" /usr/local/sbin/bad-apply-server-update
install -m 755 "${SCRIPT_DIR}/restore-site-bundle.sh" /usr/local/sbin/bad-restore-site-bundle

cd /opt/bad
python3 -m venv .venv
.venv/bin/pip install -U pip wheel
.venv/bin/pip install -e ./server

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

# ========== [3/6] БД (Postgres) ==========
step 3 "БД (Postgres role/db + schema)"
systemctl enable --now postgresql

if [[ -n "${BAD_DATABASE_URL:-}" ]]; then
  echo "  using existing BAD_DATABASE_URL from environment"
else
  PG_PASS="$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"
  if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='bad'" | grep -q 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE USER bad WITH PASSWORD '${PG_PASS}';"
  else
    sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER USER bad WITH PASSWORD '${PG_PASS}';"
  fi
  if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='bad'" | grep -q 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE bad OWNER bad;"
  fi
  # Localhost only — listen + hba
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET listen_addresses TO 'localhost';"
  PG_HBA="$(sudo -u postgres psql -tAc 'SHOW hba_file' | tr -d '[:space:]')"
  if [[ -n "${PG_HBA}" && -f "${PG_HBA}" ]]; then
    if ! grep -qE '^[[:space:]]*host[[:space:]]+bad[[:space:]]+bad[[:space:]]+127\.0\.0\.1/32' "${PG_HBA}"; then
      echo "host bad bad 127.0.0.1/32 scram-sha-256" >> "${PG_HBA}"
      echo "host bad bad ::1/128 scram-sha-256" >> "${PG_HBA}"
    fi
  fi
  systemctl restart postgresql
  BAD_DATABASE_URL="postgresql://bad:${PG_PASS}@127.0.0.1:5432/bad"
  export BAD_DATABASE_URL
fi

DB_SUMMARY="Postgres (BAD_DATABASE_URL, localhost)"
echo "  mode: Postgres → schema"
BAD_DATABASE_URL="${BAD_DATABASE_URL}" /opt/bad/.venv/bin/python -c \
  'from bad_server.db import open_database; open_database(database_url=__import__("os").environ["BAD_DATABASE_URL"]); print("  schema: ok")'

if [[ ! -f "${SITE_ENV}" ]]; then
  ENROLLMENT_TOKEN="bad_en_$(openssl rand -base64 48 | tr -d '/+=' | head -c 48)"
  ADMIN_TOKEN="bad_ad_$(openssl rand -base64 48 | tr -d '/+=' | head -c 48)"
  umask 077
  cat > "${SITE_ENV}" <<EOF
BAD_DATABASE_URL=${BAD_DATABASE_URL}
BAD_DOMAIN=${BAD_DOMAIN}
BAD_ENROLLMENT_TOKEN=${ENROLLMENT_TOKEN}
BAD_ADMIN_TOKEN=${ADMIN_TOKEN}
BAD_DATA_KEY_FILE=/etc/bad/data_key
BAD_SESSION_SECRET_FILE=/etc/bad/session_secret
BAD_COOKIE_SECURE=${COOKIE_SECURE}
BAD_GITHUB_REPO=${BAD_GITHUB_REPO:-blazerity/bAD}
BAD_AGENT_UPDATES_DIR=/var/lib/bad/agent-updates
BAD_SERVER_RELEASES_DIR=/var/lib/bad/server-releases
BAD_BACKUP_DIR=/var/lib/bad/backups
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
  if ! grep -q '^BAD_DATABASE_URL=' "${SITE_ENV}" 2>/dev/null; then
    if [[ -z "${BAD_DATABASE_URL:-}" ]]; then
      echo "error: site.env без BAD_DATABASE_URL — задайте URL (Postgres only)" >&2
      exit 1
    fi
    printf '\nBAD_DATABASE_URL=%s\n' "${BAD_DATABASE_URL}" >> "${SITE_ENV}"
    chown root:bad "${SITE_ENV}"
    chmod 640 "${SITE_ENV}"
  fi
  # Убрать устаревший BAD_DB_PATH если остался рядом с URL
  if grep -q '^BAD_DB_PATH=' "${SITE_ENV}" 2>/dev/null && grep -q '^BAD_DATABASE_URL=' "${SITE_ENV}"; then
    sed -i '/^BAD_DB_PATH=/d' "${SITE_ENV}"
    chown root:bad "${SITE_ENV}"
    chmod 640 "${SITE_ENV}"
  fi
fi

chown -R bad:bad /opt/bad
chmod -R u+rwX,g+rX,o-rwx /opt/bad

# ========== [4/6] systemd ==========
step 4 "systemd bad-api (+ tls-apply / server-update path)"
install -m 644 "${SCRIPT_DIR}/systemd/bad-api.service" /etc/systemd/system/bad-api.service
install -m 644 "${SCRIPT_DIR}/systemd/bad-tls-apply.service" /etc/systemd/system/bad-tls-apply.service
install -m 644 "${SCRIPT_DIR}/systemd/bad-tls-apply.path" /etc/systemd/system/bad-tls-apply.path
install -m 644 "${SCRIPT_DIR}/systemd/bad-server-update-apply.service" /etc/systemd/system/bad-server-update-apply.service
install -m 644 "${SCRIPT_DIR}/systemd/bad-server-update-apply.path" /etc/systemd/system/bad-server-update-apply.path
systemctl daemon-reload
systemctl enable --now bad-api.service
systemctl enable --now bad-tls-apply.path
systemctl enable --now bad-server-update-apply.path

# ========== [5/6] nginx ==========
step 5 "nginx"
BAD_NGINX_TEMPLATE_DIR=/opt/bad/deploy/debian/nginx /usr/local/sbin/bad-apply-tls
systemctl enable --now nginx

if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  if ufw status | grep -qi inactive; then
    echo "warning: enabling ufw with allow 22,80,443 — ensure SSH access is correct" >&2
    ufw --force enable || true
  fi
fi

for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/v1/health >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

SCHEME="https"
if [[ "${HAS_TLS}" -eq 0 ]]; then
  SCHEME="http"
fi

# ========== [6/6] Готово + памятка ==========
step 6 "Готово"
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
echo " DB:               ${DB_SUMMARY}"
echo " Secrets:          /etc/bad/data_key + /etc/bad/session_secret (not in DB dumps)"
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
echo
echo "----------------------------------------"
echo " Что дальше"
echo "----------------------------------------"
if [[ "${HAS_TLS}" -eq 0 ]]; then
  echo " 1. Откройте панель:  ${SCHEME}://${BAD_DOMAIN}/login"
  echo "    (без cert при install — только из LAN/VPN/ssh -L, не в интернет)"
  echo " 2. Войдите admin / admin → сразу смените пароль"
  echo " 3. Параметры → Сертификат: загрузите fullchain + private key"
  echo "    → «Установить и перезагрузить nginx»"
  echo " 4. Откройте https://${BAD_DOMAIN}/ и войдите снова"
  echo " 5. Только после HTTPS — MSI агентов:"
  echo "    SERVERURL=https://${BAD_DOMAIN} ENROLLMENTTOKEN=<enrollment>"
else
  echo " 1. Откройте панель:  https://${BAD_DOMAIN}/login"
  echo " 2. Войдите admin / admin → сразу смените пароль"
  echo " 3. Cert уже при install — ротация позже через Параметры → Сертификат"
  echo " 4. (уже HTTPS)"
  echo " 5. MSI агентов:"
  echo "    SERVERURL=https://${BAD_DOMAIN} ENROLLMENTTOKEN=<enrollment>"
fi
echo " 6. После волны MSI — смените enrollment token"
echo "    (Параметры → Обновления агента → Сменить enrollment token)"
echo "    и обновите Intune/GPO. Не шарьте msiexec-логи."
echo
echo " Ключи: /etc/bad/data_key + session_secret — не в daily DB-бэкапе."
echo " Полный DR: site bundle (Параметры → Резервные копии), только по HTTPS."
echo " Подробнее: docs/operator-guide.md"
echo "----------------------------------------"
