#!/usr/bin/env bash
# Root helper: staging → /etc/bad/tls/{fullchain,privkey}.pem, nginx HTTP/HTTPS, reload.
# Trigger: systemd path bad-tls-apply.path → bad-tls-apply.service
set -euo pipefail

TLS_DIR="${BAD_TLS_DIR:-/etc/bad/tls}"
STAGING="${TLS_DIR}/staging"
CERT="${TLS_DIR}/fullchain.pem"
KEY="${TLS_DIR}/privkey.pem"
STAGE_CERT="${STAGING}/fullchain.pem"
STAGE_KEY="${STAGING}/privkey.pem"
STATUS="${TLS_DIR}/apply.status"
SITE_ENV=/etc/bad/site.env
NGINX_SITE=/etc/nginx/sites-available/bad
TEMPLATE_DIR="${BAD_NGINX_TEMPLATE_DIR:-/opt/bad/deploy/debian/nginx}"

if [[ ! -d "${TEMPLATE_DIR}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  TEMPLATE_DIR="$(cd "${SCRIPT_DIR}/nginx" && pwd)"
fi

write_status() {
  local ok="$1" msg="$2" mode="$3"
  mkdir -p "${TLS_DIR}"
  umask 027
  python3 - <<PY
import json
from datetime import datetime, timezone
ok = ${ok}
msg = $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${msg}")
mode = $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${mode}")
data = {
  "ok": ok,
  "message": msg,
  "mode": mode,
  "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
}
open("${STATUS}.tmp","w",encoding="utf-8").write(json.dumps(data, ensure_ascii=False) + "\n")
PY
  mv "${STATUS}.tmp" "${STATUS}"
  chmod 640 "${STATUS}" || true
  chown root:bad "${STATUS}" 2>/dev/null || true
}

read_domain() {
  local domain=""
  if [[ -f "${SITE_ENV}" ]] && grep -q '^BAD_DOMAIN=' "${SITE_ENV}"; then
    domain="$(grep '^BAD_DOMAIN=' "${SITE_ENV}" | head -1 | cut -d= -f2- | tr -d "\"'")"
  fi
  if [[ -z "${domain}" ]]; then
    domain="_"
  fi
  printf '%s' "${domain}"
}

pair_ok() {
  local cert="$1" key="$2"
  python3 - <<'PY' "${cert}" "${key}"
import sys
import re
from cryptography import x509
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
cert_pem = open(sys.argv[1], "rb").read()
key_pem = open(sys.argv[2], "rb").read()
blocks = re.findall(br"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", cert_pem, re.S)
if not blocks:
    sys.exit(2)
leaf = x509.load_pem_x509_certificate(blocks[0] + b"\n")
key = load_pem_private_key(key_pem, password=None)
a = leaf.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
b = key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
sys.exit(0 if a == b else 1)
PY
}

ensure_tls_dirs() {
  mkdir -p "${TLS_DIR}" "${STAGING}"
  # Group-writable so user bad can stage uploads + apply.request
  chown root:bad "${TLS_DIR}" 2>/dev/null || true
  chmod 770 "${TLS_DIR}" || true
  chown bad:bad "${STAGING}" 2>/dev/null || chown root:bad "${STAGING}" 2>/dev/null || true
  chmod 770 "${STAGING}" || true
}

promote_staging() {
  if [[ ! -f "${STAGE_CERT}" || ! -f "${STAGE_KEY}" ]]; then
    return 1
  fi
  if ! openssl x509 -in "${STAGE_CERT}" -noout >/dev/null 2>&1; then
    write_status false "Staging: сертификат невалиден" "http"
    exit 1
  fi
  if ! pair_ok "${STAGE_CERT}" "${STAGE_KEY}"; then
    write_status false "Staging: private key не пара к сертификату" "http"
    exit 1
  fi
  if [[ -f "${CERT}" ]]; then
    cp -a "${CERT}" "${CERT}.bak" || true
  fi
  if [[ -f "${KEY}" ]]; then
    cp -a "${KEY}" "${KEY}.bak" || true
  fi
  # Replace symlinks with real managed files
  rm -f "${CERT}" "${KEY}"
  install -m 644 -o root -g root "${STAGE_CERT}" "${CERT}"
  install -m 600 -o root -g root "${STAGE_KEY}" "${KEY}"
  if command -v setfacl >/dev/null 2>&1 && getent passwd www-data >/dev/null; then
    setfacl -m u:www-data:r "${KEY}" 2>/dev/null || true
    setfacl -m u:www-data:r "${CERT}" 2>/dev/null || true
  fi
  rm -f "${STAGE_KEY}"
  return 0
}

apply_nginx() {
  local mode="$1" domain="$2"
  local template
  if [[ "${mode}" == "https" ]]; then
    template="${TEMPLATE_DIR}/bad.conf.template"
  else
    template="${TEMPLATE_DIR}/bad-http.conf.template"
  fi
  if [[ ! -f "${template}" ]]; then
    write_status false "Нет nginx template: ${template}" "${mode}"
    exit 1
  fi
  local tmpdir out
  tmpdir="$(mktemp -d)"
  out="${tmpdir}/bad.conf"
  sed \
    -e "s|__BAD_DOMAIN__|${domain}|g" \
    -e "s|__BAD_TLS_CERT__|${CERT}|g" \
    -e "s|__BAD_TLS_KEY__|${KEY}|g" \
    "${template}" > "${out}"
  if [[ -f "${NGINX_SITE}" ]]; then
    cp -a "${NGINX_SITE}" "${NGINX_SITE}.bak" || true
  fi
  install -m 644 "${out}" "${NGINX_SITE}"
  ln -sfn "${NGINX_SITE}" /etc/nginx/sites-enabled/bad
  rm -f /etc/nginx/sites-enabled/default
  if ! nginx -t 2>"${tmpdir}/nginx-t.err"; then
    err="$(tr '\n' ' ' < "${tmpdir}/nginx-t.err" | head -c 400)"
    if [[ -f "${NGINX_SITE}.bak" ]]; then
      mv "${NGINX_SITE}.bak" "${NGINX_SITE}"
      nginx -t >/dev/null 2>&1 || true
    fi
    if [[ -f "${CERT}.bak" ]]; then mv "${CERT}.bak" "${CERT}"; fi
    if [[ -f "${KEY}.bak" ]]; then mv "${KEY}.bak" "${KEY}"; fi
    write_status false "nginx -t failed: ${err}" "${mode}"
    rm -rf "${tmpdir}"
    exit 1
  fi
  systemctl enable nginx >/dev/null 2>&1 || true
  systemctl reload nginx || systemctl restart nginx
  rm -rf "${tmpdir}"
  rm -f "${NGINX_SITE}.bak" "${CERT}.bak" "${KEY}.bak"
}

update_cookie_secure() {
  local mode="$1"
  [[ -f "${SITE_ENV}" ]] || return 0
  local val=0
  [[ "${mode}" == "https" ]] && val=1
  if grep -q '^BAD_COOKIE_SECURE=' "${SITE_ENV}"; then
    sed -i "s/^BAD_COOKIE_SECURE=.*/BAD_COOKIE_SECURE=${val}/" "${SITE_ENV}"
  else
    printf '\nBAD_COOKIE_SECURE=%s\n' "${val}" >> "${SITE_ENV}"
  fi
}

detect_mode() {
  if [[ -e "${CERT}" && -e "${KEY}" ]] && pair_ok "${CERT}" "${KEY}" 2>/dev/null; then
    printf '%s' "https"
  else
    printf '%s' "http"
  fi
}

ensure_tls_dirs

domain="$(read_domain)"
promoted=0
if [[ -f "${STAGE_CERT}" && -f "${STAGE_KEY}" ]]; then
  promote_staging
  promoted=1
fi

mode="$(detect_mode)"
apply_nginx "${mode}" "${domain}"
update_cookie_secure "${mode}"

msg="nginx ${mode} применён (reload ok)"
if [[ "${promoted}" -eq 1 ]]; then
  msg="Сертификат установлен; ${msg}"
fi
write_status true "${msg}" "${mode}"

# Deferred restart so upload HTTP response can finish; picks up BAD_COOKIE_SECURE.
(
  sleep 2
  systemctl try-restart bad-api.service >/dev/null 2>&1 || true
) &
disown 2>/dev/null || true

echo "bad-apply-tls: mode=${mode} domain=${domain} promoted=${promoted}"
