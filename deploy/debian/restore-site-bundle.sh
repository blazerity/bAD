#!/usr/bin/env bash
# Восстановление site bundle bAD (DB + keys + MSI mirror).
# Использование:
#   sudo bash restore-site-bundle.sh /path/to/bad-site-bundle-....tar.gz
# Осторожно: перезаписывает /var/lib/bad/bad.db и ключи в /etc/bad.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "error: must run as root" >&2
  exit 1
fi

BUNDLE="${1:-}"
if [[ -z "${BUNDLE}" || ! -f "${BUNDLE}" ]]; then
  echo "usage: $0 /path/to/bad-site-bundle-YYYYMMDDThhmmssZ.tar.gz" >&2
  exit 1
fi

TMP="$(mktemp -d /tmp/bad-restore.XXXXXX)"
cleanup() { rm -rf "${TMP}"; }
trap cleanup EXIT

echo "Extracting bundle to ${TMP}"
tar -xzf "${BUNDLE}" -C "${TMP}"

if [[ ! -f "${TMP}/manifest.json" ]]; then
  echo "error: manifest.json missing — not a bad site bundle?" >&2
  exit 1
fi
if [[ ! -f "${TMP}/bad.db" ]]; then
  echo "error: bad.db missing in bundle" >&2
  exit 1
fi

echo "Stopping bad-api..."
systemctl stop bad-api.service || true

mkdir -p /var/lib/bad /var/lib/bad/agent-updates /etc/bad
BACKUP_TS="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -f /var/lib/bad/bad.db ]]; then
  cp -a /var/lib/bad/bad.db "/var/lib/bad/bad.db.pre-restore-${BACKUP_TS}"
  echo "Previous DB saved as bad.db.pre-restore-${BACKUP_TS}"
fi

install -m 600 -o bad -g bad "${TMP}/bad.db" /var/lib/bad/bad.db
# Drop WAL/SHM so restored snapshot is authoritative.
rm -f /var/lib/bad/bad.db-wal /var/lib/bad/bad.db-shm

if [[ -d "${TMP}/keys" ]]; then
  shopt -s nullglob
  for f in "${TMP}/keys"/*; do
    base="$(basename "${f}")"
    dest="/etc/bad/${base}"
    if [[ -f "${dest}" ]]; then
      cp -a "${dest}" "${dest}.pre-restore-${BACKUP_TS}"
    fi
    install -m 440 -o root -g bad "${f}" "${dest}"
    echo "Restored key file: ${dest}"
  done
  shopt -u nullglob
fi

if [[ -d "${TMP}/agent-updates/files" ]]; then
  shopt -s nullglob
  for f in "${TMP}/agent-updates/files"/*; do
    install -m 640 -o bad -g bad "${f}" "/var/lib/bad/agent-updates/$(basename "${f}")"
  done
  shopt -u nullglob
  echo "Restored MSI files into /var/lib/bad/agent-updates"
fi
if [[ -f "${TMP}/agent-updates/manifest.json" ]]; then
  install -m 640 -o bad -g bad \
    "${TMP}/agent-updates/manifest.json" \
    /var/lib/bad/agent-updates/bundle-manifest.json
fi

chown bad:bad /var/lib/bad/bad.db
chmod 600 /var/lib/bad/bad.db

echo "Starting bad-api..."
systemctl start bad-api.service
sleep 1
if curl -fsS http://127.0.0.1:8000/v1/health >/dev/null 2>&1; then
  echo "Restore OK — health responds."
else
  echo "warning: health check failed; inspect: journalctl -u bad-api -n 50" >&2
  exit 1
fi
