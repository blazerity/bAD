#!/usr/bin/env bash
# Root helper: GitHub tarball / rollback slot → /opt/bad + try-restart bad-api.
# Trigger: systemd path bad-server-update-apply.path → bad-server-update-apply.service
set -euo pipefail

RELEASES_DIR="${BAD_SERVER_RELEASES_DIR:-/var/lib/bad/server-releases}"
OPT_BAD="${BAD_OPT_DIR:-/opt/bad}"
SITE_ENV="${BAD_SITE_ENV:-/etc/bad/site.env}"
REQUEST="${RELEASES_DIR}/apply.request"
STATUS="${RELEASES_DIR}/apply.status"
CURRENT="${RELEASES_DIR}/current.json"
SLOTS="${RELEASES_DIR}/slots"
STAGING="${RELEASES_DIR}/staging"
MAX_PAST="${BAD_SERVER_UPDATE_MAX_PAST:-3}"
API_BASE_DEFAULT="https://api.github.com"

write_status() {
  local ok="$1" msg="$2" action="$3"
  mkdir -p "${RELEASES_DIR}"
  umask 027
  python3 - "${STATUS}" "${ok}" "${msg}" "${action}" <<'PY'
import json, sys
from datetime import datetime, timezone
status_path, ok_s, msg, action = sys.argv[1:5]
data = {
  "ok": ok_s.lower() in ("true", "1", "yes"),
  "message": msg,
  "action": action,
  "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
}
tmp = status_path + ".tmp"
open(tmp, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False) + "\n")
PY
  mv "${STATUS}.tmp" "${STATUS}"
  chmod 640 "${STATUS}" || true
  chown root:bad "${STATUS}" 2>/dev/null || true
}

fail() {
  local msg="$1" action="${2:-unknown}"
  write_status false "${msg}" "${action}"
  echo "bad-apply-server-update: FAIL ${msg}" >&2
  exit 1
}

ensure_dirs() {
  mkdir -p "${RELEASES_DIR}" "${SLOTS}" "${STAGING}"
  chown root:bad "${RELEASES_DIR}" 2>/dev/null || true
  chmod 770 "${RELEASES_DIR}" || true
  chown bad:bad "${STAGING}" 2>/dev/null || chown root:bad "${STAGING}" 2>/dev/null || true
  chmod 770 "${STAGING}" || true
  # 750: bad читает слоты, не пишет tree (spot-check should)
  chown root:bad "${SLOTS}" 2>/dev/null || true
  chmod 750 "${SLOTS}" || true
}

read_site_env_var() {
  local key="$1" default="${2:-}"
  if [[ -f "${SITE_ENV}" ]] && grep -q "^${key}=" "${SITE_ENV}"; then
    grep "^${key}=" "${SITE_ENV}" | head -1 | cut -d= -f2- | tr -d "\"'"
  else
    printf '%s' "${default}"
  fi
}

github_token() {
  local tok file
  tok="$(read_site_env_var BAD_GITHUB_TOKEN "")"
  if [[ -n "${tok}" ]]; then
    printf '%s' "${tok}"
    return 0
  fi
  file="$(read_site_env_var BAD_GITHUB_TOKEN_FILE "")"
  if [[ -n "${file}" && -f "${file}" ]]; then
    tr -d '\r\n' < "${file}"
    return 0
  fi
  if [[ -n "${BAD_GITHUB_TOKEN:-}" ]]; then
    printf '%s' "${BAD_GITHUB_TOKEN}"
    return 0
  fi
  printf ''
}

set_token_in_site_env() {
  local tok_file="${STAGING}/github_token.staging"
  [[ -f "${tok_file}" ]] || fail "нет staging github_token" "set_token"
  local tok
  tok="$(tr -d '\r\n' < "${tok_file}")"
  [[ -n "${tok}" ]] || fail "пустой github token" "set_token"
  mkdir -p "$(dirname "${SITE_ENV}")"
  if [[ -f "${SITE_ENV}" ]]; then
    if grep -q '^BAD_GITHUB_TOKEN=' "${SITE_ENV}"; then
      sed -i "s|^BAD_GITHUB_TOKEN=.*|BAD_GITHUB_TOKEN=${tok}|" "${SITE_ENV}"
    else
      printf '\nBAD_GITHUB_TOKEN=%s\n' "${tok}" >> "${SITE_ENV}"
    fi
  else
    printf 'BAD_GITHUB_TOKEN=%s\n' "${tok}" > "${SITE_ENV}"
  fi
  chown root:bad "${SITE_ENV}" 2>/dev/null || true
  chmod 640 "${SITE_ENV}" || true
  # Файл 440 — процесс bad читает без restart (Settings.github_token_file).
  local tok_persist="${BAD_GITHUB_TOKEN_FILE_PATH:-/etc/bad/github_token}"
  mkdir -p "$(dirname "${tok_persist}")"
  printf '%s\n' "${tok}" > "${tok_persist}"
  chown root:bad "${tok_persist}" 2>/dev/null || true
  chmod 440 "${tok_persist}" || true
  if ! grep -q '^BAD_GITHUB_TOKEN_FILE=' "${SITE_ENV}" 2>/dev/null; then
    printf '\nBAD_GITHUB_TOKEN_FILE=%s\n' "${tok_persist}" >> "${SITE_ENV}"
  fi
  rm -f "${tok_file}"
  write_status true "BAD_GITHUB_TOKEN записан в site.env + файл токена (plaintext в UI не отдаётся)" "set_token"
  echo "bad-apply-server-update: set_token ok"
  exit 0
}

read_request() {
  [[ -f "${REQUEST}" ]] || fail "нет apply.request" "unknown"
  python3 - "${REQUEST}" <<'PY'
import json, sys
path = sys.argv[1]
data = json.loads(open(path, encoding="utf-8").read())
if not isinstance(data, dict):
    raise SystemExit("corrupt request")
for k in ("action", "branch", "sha", "slot_id", "requested_at"):
    v = data.get(k)
    if v is None:
        v = ""
    print(f"{k}={v}")
PY
}

write_slot_meta() {
  # path slot_id branch sha version source
  python3 - "$@" <<'PY'
import json, sys
from datetime import datetime, timezone
path, slot_id, branch, sha, version, source = sys.argv[1:7]
meta = {
  "slot_id": slot_id,
  "branch": branch or None,
  "sha": sha or None,
  "version": version or None,
  "installed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
  "source": source,
}
open(path, "w", encoding="utf-8").write(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
PY
}

archive_current_slot() {
  # Сохранить текущий /opt/bad/server в слот, если есть current.json с sha.
  [[ -f "${CURRENT}" ]] || return 0
  local branch sha slot_id version
  eval "$(python3 - "${CURRENT}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
sha = str(d.get("sha") or "")
branch = str(d.get("branch") or "unknown")
slot_id = str(d.get("slot_id") or "")
version = str(d.get("version") or "")
print(f"branch={branch!r}")
print(f"sha={sha!r}")
print(f"slot_id={slot_id!r}")
print(f"version={version!r}")
PY
)"
  [[ -n "${sha}" ]] || return 0
  if [[ -z "${slot_id}" ]]; then
    local bsafe
    bsafe="$(printf '%s' "${branch}" | tr '/' '_')"
    slot_id="${bsafe}_${sha:0:12}"
  fi
  local dest="${SLOTS}/${slot_id}"
  if [[ -d "${dest}/tree/server" ]]; then
    return 0
  fi
  mkdir -p "${dest}/tree"
  if [[ -d "${OPT_BAD}/server" ]]; then
    rm -rf "${dest}/tree/server"
    cp -a "${OPT_BAD}/server" "${dest}/tree/server"
  fi
  if [[ -d "${OPT_BAD}/deploy" ]]; then
    rm -rf "${dest}/tree/deploy"
    cp -a "${OPT_BAD}/deploy" "${dest}/tree/deploy"
  fi
  if [[ -f "${OPT_BAD}/VERSION" ]]; then
    cp -a "${OPT_BAD}/VERSION" "${dest}/tree/VERSION"
  fi
  # VERSION at repo root is copied beside opt in install; also check /opt/bad/VERSION
  [[ -f /opt/bad/VERSION ]] && cp -a /opt/bad/VERSION "${dest}/tree/VERSION" || true
  write_slot_meta "${dest}/meta.json" "${slot_id}" "${branch}" "${sha}" "${version}" "archive"
  chown -R root:bad "${dest}" 2>/dev/null || true
}

download_and_fill_slot() {
  local branch="$1" sha="$2"
  local repo api token slot_id dest tarball tmp
  repo="$(read_site_env_var BAD_GITHUB_REPO "${BAD_GITHUB_REPO:-blazerity/bAD}")"
  api="$(read_site_env_var BAD_GITHUB_API_BASE "${BAD_GITHUB_API_BASE:-$API_BASE_DEFAULT}")"
  token="$(github_token)"
  [[ -n "${sha}" ]] || fail "SHA пуст для apply" "apply"
  local bsafe
  bsafe="$(printf '%s' "${branch}" | tr '/' '_')"
  slot_id="${bsafe}_${sha:0:12}"
  dest="${SLOTS}/${slot_id}"
  mkdir -p "${dest}/tree"
  tmp="$(mktemp -d)"
  tarball="${tmp}/src.tgz"
  local url="${api%/}/repos/${repo}/tarball/${sha}"
  local curl_args=(-fsSL -o "${tarball}" -H "Accept: application/vnd.github+json" -H "User-Agent: bad-apply-server-update/1.0")
  if [[ -n "${token}" ]]; then
    curl_args+=(-H "Authorization: Bearer ${token}")
  fi
  if ! curl "${curl_args[@]}" "${url}"; then
    rm -rf "${tmp}"
    fail "не удалось скачать tarball ${repo}@${sha:0:12}" "apply"
  fi
  mkdir -p "${tmp}/extract"
  if ! tar -xzf "${tarball}" -C "${tmp}/extract" --strip-components=1; then
    rm -rf "${tmp}"
    fail "повреждённый tarball" "apply"
  fi
  [[ -d "${tmp}/extract/server" ]] || { rm -rf "${tmp}"; fail "в архиве нет server/" "apply"; }
  rm -rf "${dest}/tree/server" "${dest}/tree/deploy" "${dest}/tree/VERSION"
  cp -a "${tmp}/extract/server" "${dest}/tree/server"
  if [[ -d "${tmp}/extract/deploy" ]]; then
    cp -a "${tmp}/extract/deploy" "${dest}/tree/deploy"
  fi
  if [[ -f "${tmp}/extract/VERSION" ]]; then
    cp -a "${tmp}/extract/VERSION" "${dest}/tree/VERSION"
  fi
  local version=""
  if [[ -f "${dest}/tree/VERSION" ]]; then
    version="$(head -1 "${dest}/tree/VERSION" | tr -d '\r\n')"
  fi
  write_slot_meta "${dest}/meta.json" "${slot_id}" "${branch}" "${sha}" "${version}" "apply"
  rm -rf "${tmp}"
  chown -R root:bad "${dest}" 2>/dev/null || true
  printf '%s' "${slot_id}"
}

promote_slot() {
  local slot_id="$1" source_label="$2"
  local dest="${SLOTS}/${slot_id}"
  [[ -d "${dest}/tree/server" ]] || fail "слот ${slot_id}: нет tree/server" "${source_label}"
  mkdir -p "${OPT_BAD}"
  # Atomic-ish replace of server tree
  local new_server="${OPT_BAD}/.server.next"
  local bak_server="${OPT_BAD}/.server.bak"
  rm -rf "${new_server}"
  cp -a "${dest}/tree/server" "${new_server}"
  if [[ -d "${OPT_BAD}/server" ]]; then
    rm -rf "${bak_server}"
    mv "${OPT_BAD}/server" "${bak_server}"
  fi
  mv "${new_server}" "${OPT_BAD}/server"
  rm -rf "${bak_server}"

  if [[ -d "${dest}/tree/deploy" ]]; then
    mkdir -p "${OPT_BAD}/deploy"
    # Refresh debian helpers used by install/ops
    if [[ -d "${dest}/tree/deploy/debian" ]]; then
      mkdir -p "${OPT_BAD}/deploy/debian"
      cp -a "${dest}/tree/deploy/debian/." "${OPT_BAD}/deploy/debian/"
      if [[ -f "${OPT_BAD}/deploy/debian/bad-apply-tls.sh" ]]; then
        install -m 755 "${OPT_BAD}/deploy/debian/bad-apply-tls.sh" /usr/local/sbin/bad-apply-tls
      fi
      if [[ -f "${OPT_BAD}/deploy/debian/bad-apply-server-update.sh" ]]; then
        install -m 755 "${OPT_BAD}/deploy/debian/bad-apply-server-update.sh" /usr/local/sbin/bad-apply-server-update
      fi
    fi
  fi
  if [[ -f "${dest}/tree/VERSION" ]]; then
    cp -a "${dest}/tree/VERSION" "${OPT_BAD}/VERSION"
  fi

  chown -R bad:bad "${OPT_BAD}/server" 2>/dev/null || true
  if [[ -d "${OPT_BAD}/.venv" ]]; then
    # Reinstall editable package into existing venv
    if ! "${OPT_BAD}/.venv/bin/pip" install -e "${OPT_BAD}/server" >/tmp/bad-server-update-pip.log 2>&1; then
      fail "pip install -e server не удался (см. /tmp/bad-server-update-pip.log)" "${source_label}"
    fi
  fi

  local branch sha version
  eval "$(python3 - "${dest}/meta.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(f"branch={str(d.get('branch') or '')!r}")
print(f"sha={str(d.get('sha') or '')!r}")
print(f"version={str(d.get('version') or '')!r}")
PY
)"
  write_slot_meta "${CURRENT}" "${slot_id}" "${branch}" "${sha}" "${version}" "${source_label}"
  chmod 640 "${CURRENT}" || true
  chown root:bad "${CURRENT}" 2>/dev/null || true

  # Update slot meta source/time for promote
  write_slot_meta "${dest}/meta.json" "${slot_id}" "${branch}" "${sha}" "${version}" "${source_label}"
}

prune_slots() {
  python3 - "${SLOTS}" "${CURRENT}" "${MAX_PAST}" <<'PY'
import json, os, shutil, sys
slots_dir, current_path, max_past_s = sys.argv[1:4]
max_past = int(max_past_s)
current_id = ""
if os.path.isfile(current_path):
    try:
        current_id = str(json.load(open(current_path, encoding="utf-8")).get("slot_id") or "")
    except Exception:
        current_id = ""
items = []
if os.path.isdir(slots_dir):
    for name in os.listdir(slots_dir):
        path = os.path.join(slots_dir, name)
        if not os.path.isdir(path):
            continue
        meta_path = os.path.join(path, "meta.json")
        meta = {}
        if os.path.isfile(meta_path):
            try:
                meta = json.load(open(meta_path, encoding="utf-8"))
            except Exception:
                meta = {}
        slot_id = str(meta.get("slot_id") or name)
        items.append((str(meta.get("installed_at") or ""), slot_id, path))
# Keep current + newest past (max_past)
items.sort(key=lambda t: t[0], reverse=True)
kept = 0
for _ts, slot_id, path in items:
    if slot_id == current_id:
        continue
    if kept < max_past:
        kept += 1
        continue
    shutil.rmtree(path, ignore_errors=True)
PY
}

restart_api() {
  systemctl try-restart bad-api.service || systemctl restart bad-api.service || true
}

# ---- main ----
ensure_dirs

if [[ ! -f "${REQUEST}" ]]; then
  echo "bad-apply-server-update: no request, exit"
  exit 0
fi

# Parse request into env-like lines
eval "$(read_request | sed 's/^/REQ_/')"
ACTION="${REQ_action:-}"
BRANCH="${REQ_branch:-}"
SHA="${REQ_sha:-}"
SLOT_ID="${REQ_slot_id:-}"

case "${ACTION}" in
  set_token)
    set_token_in_site_env
    ;;
  apply)
    [[ -n "${BRANCH}" ]] || BRANCH="main"
    if [[ -z "${SHA}" ]]; then
      repo="$(read_site_env_var BAD_GITHUB_REPO "${BAD_GITHUB_REPO:-blazerity/bAD}")"
      api="$(read_site_env_var BAD_GITHUB_API_BASE "${BAD_GITHUB_API_BASE:-$API_BASE_DEFAULT}")"
      token="$(github_token)"
      enc_branch="$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "${BRANCH}")"
      hdr=(-H "Accept: application/vnd.github+json" -H "User-Agent: bad-apply-server-update/1.0")
      if [[ -n "${token}" ]]; then
        hdr+=(-H "Authorization: Bearer ${token}")
      fi
      SHA="$(curl -fsSL "${hdr[@]}" "${api%/}/repos/${repo}/commits/${enc_branch}" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("sha") or "")')"
      [[ -n "${SHA}" ]] || fail "не удалось получить HEAD ветки ${BRANCH}" "apply"
    fi
    archive_current_slot
    SLOT_ID="$(download_and_fill_slot "${BRANCH}" "${SHA}")"
    promote_slot "${SLOT_ID}" "apply"
    prune_slots
    write_status true "Установлено ${BRANCH}@${SHA:0:12}; bad-api restart" "apply"
    restart_api
    ;;
  rollback)
    [[ -n "${SLOT_ID}" ]] || fail "slot_id обязателен для rollback" "rollback"
    [[ -d "${SLOTS}/${SLOT_ID}" ]] || fail "слот не найден: ${SLOT_ID}" "rollback"
    archive_current_slot
    promote_slot "${SLOT_ID}" "rollback"
    prune_slots
    write_status true "Откат на слот ${SLOT_ID}; bad-api restart" "rollback"
    restart_api
    ;;
  *)
    fail "неизвестное action=${ACTION}" "unknown"
    ;;
esac

echo "bad-apply-server-update: action=${ACTION} ok"
