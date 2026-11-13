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
BAD_PYTHON="${BAD_PYTHON:-python3}"

init_bad_python() {
  local here server_repo parts=() joined
  if [[ -x "${OPT_BAD}/.venv/bin/python" ]]; then
    BAD_PYTHON="${OPT_BAD}/.venv/bin/python"
  fi
  if [[ -d "${OPT_BAD}/server/bad_server" ]]; then
    parts+=("${OPT_BAD}/server")
  fi
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  server_repo="$(cd "${here}/../../server" 2>/dev/null && pwd || true)"
  if [[ -n "${server_repo}" && -d "${server_repo}/bad_server" ]]; then
    parts+=("${server_repo}")
  fi
  if [[ ${#parts[@]} -eq 0 ]]; then
    return 0
  fi
  joined="$(IFS=:; printf '%s' "${parts[*]}")"
  if [[ -n "${PYTHONPATH:-}" ]]; then
    export PYTHONPATH="${joined}:${PYTHONPATH}"
  else
    export PYTHONPATH="${joined}"
  fi
}

sanitize_field() {
  local kind="$1" value="$2"
  "${BAD_PYTHON}" - "${kind}" "${value}" <<'PY'
import sys
kind, value = sys.argv[1], sys.argv[2]
try:
    from bad_server.server_update import sanitize_branch, sanitize_sha, sanitize_slot_id
except Exception as exc:
    sys.stderr.write("import bad_server.server_update failed: %s\n" % exc)
    raise SystemExit(1)
fn = {"branch": sanitize_branch, "sha": sanitize_sha, "slot": sanitize_slot_id}.get(kind)
if fn is None:
    sys.stderr.write("unknown field\n")
    raise SystemExit(1)
try:
    sys.stdout.write(fn(value))
except Exception as exc:
    sys.stderr.write("%s\n" % exc)
    raise SystemExit(1)
PY
}

read_meta_fields() {
  "${BAD_PYTHON}" - "$1" <<'PY'
import json, sys
path = sys.argv[1]
try:
    from bad_server.server_update import sanitize_branch, sanitize_sha, sanitize_slot_id
except Exception as exc:
    sys.stderr.write("import bad_server.server_update failed: %s\n" % exc)
    raise SystemExit(1)

def clean(raw, fn):
    if raw is None:
        return ""
    raw = str(raw)
    if raw == "":
        return ""
    return fn(raw)

try:
    data = json.load(open(path, encoding="utf-8"))
except Exception as exc:
    sys.stderr.write("corrupt meta: %s\n" % exc)
    raise SystemExit(1)
if not isinstance(data, dict):
    sys.stderr.write("corrupt meta\n")
    raise SystemExit(1)
try:
    branch = clean(data.get("branch"), sanitize_branch)
    sha = clean(data.get("sha"), sanitize_sha)
    slot = clean(data.get("slot_id"), sanitize_slot_id)
except Exception as exc:
    sys.stderr.write("%s\n" % exc)
    raise SystemExit(1)
version = data.get("version")
if version is None:
    version = ""
version = str(version)
if "\n" in version or "\r" in version or "\0" in version:
    sys.stderr.write("некорректная version\n")
    raise SystemExit(1)
sys.stdout.write(branch + "\n" + sha + "\n" + slot + "\n" + version + "\n")
PY
}

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
  local tok_persist="${BAD_GITHUB_TOKEN_FILE_PATH:-/etc/bad/github_token}"
  local errfile err
  [[ -f "${tok_file}" ]] || fail "нет staging github_token" "set_token"
  errfile="$(mktemp)"
  if ! "${BAD_PYTHON}" - "${tok_file}" "${SITE_ENV}" "${tok_persist}" 2>"${errfile}" <<'PY'
import os, sys
tok_file, site_env, tok_persist = sys.argv[1:4]
raw = open(tok_file, "rb").read()
if b"\0" in raw:
    sys.stderr.write("токен содержит NUL\n")
    raise SystemExit(1)
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError:
    sys.stderr.write("токен не utf-8\n")
    raise SystemExit(1)
if text.endswith("\n"):
    text = text[:-1]
if text.endswith("\r"):
    text = text[:-1]
if (not text) or ("\n" in text) or ("\r" in text) or ("\0" in text):
    sys.stderr.write("токен пуст или содержит перевод строки\n")
    raise SystemExit(1)

def write_mode(path, data, mode):
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        os.write(fd, data.encode("utf-8"))
    finally:
        os.close(fd)
    os.replace(tmp, path)

os.makedirs(os.path.dirname(site_env) or ".", exist_ok=True)
lines = []
if os.path.isfile(site_env):
    lines = open(site_env, encoding="utf-8").read().splitlines()
out = []
replaced = False
for line in lines:
    if line.startswith("BAD_GITHUB_TOKEN="):
        out.append("BAD_GITHUB_TOKEN=" + text)
        replaced = True
    else:
        out.append(line)
if not replaced:
    out.append("BAD_GITHUB_TOKEN=" + text)
file_line = "BAD_GITHUB_TOKEN_FILE=" + tok_persist
if not any(line.startswith("BAD_GITHUB_TOKEN_FILE=") for line in out):
    out.append(file_line)
write_mode(site_env, "\n".join(out) + "\n", 0o640)
os.makedirs(os.path.dirname(tok_persist) or ".", exist_ok=True)
write_mode(tok_persist, text + "\n", 0o440)
PY
  then
    err="$(head -n 1 "${errfile}" || true)"
    rm -f "${errfile}"
    fail "${err:-токен отклонён}" "set_token"
  fi
  rm -f "${errfile}"
  chown root:bad "${SITE_ENV}" 2>/dev/null || true
  chmod 640 "${SITE_ENV}" || true
  # Файл 440 — процесс bad читает без restart (Settings.github_token_file).
  chown root:bad "${tok_persist}" 2>/dev/null || true
  chmod 440 "${tok_persist}" || true
  rm -f "${tok_file}"
  write_status true "BAD_GITHUB_TOKEN записан в site.env + файл токена (plaintext в UI не отдаётся)" "set_token"
  echo "bad-apply-server-update: set_token ok"
  exit 0
}

read_request() {
  [[ -f "${REQUEST}" ]] || fail "нет apply.request" "unknown"
  "${BAD_PYTHON}" - "${REQUEST}" <<'PY'
import json, sys
path = sys.argv[1]
try:
    from bad_server.server_update import sanitize_branch, sanitize_sha, sanitize_slot_id
except Exception as exc:
    sys.stderr.write("import bad_server.server_update failed: %s\n" % exc)
    raise SystemExit(1)

def clean(raw, fn):
    if raw is None:
        return ""
    raw = str(raw)
    if raw == "":
        return ""
    return fn(raw)

try:
    data = json.loads(open(path, encoding="utf-8").read())
except Exception as exc:
    sys.stderr.write("corrupt request: %s\n" % exc)
    raise SystemExit(1)
if not isinstance(data, dict):
    sys.stderr.write("corrupt request\n")
    raise SystemExit(1)
action = str(data.get("action") or "")
if action not in ("apply", "rollback", "set_token"):
    sys.stderr.write("неизвестное action\n")
    raise SystemExit(1)
try:
    branch = clean(data.get("branch"), sanitize_branch)
    sha = clean(data.get("sha"), sanitize_sha)
    slot = clean(data.get("slot_id"), sanitize_slot_id)
except Exception as exc:
    sys.stderr.write("%s\n" % exc)
    raise SystemExit(1)
sys.stdout.write(action + "\n" + branch + "\n" + sha + "\n" + slot + "\n")
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
  local branch sha slot_id version meta errfile err bsafe
  errfile="$(mktemp)"
  if ! meta="$(read_meta_fields "${CURRENT}" 2>"${errfile}")"; then
    err="$(head -n 1 "${errfile}" || true)"
    rm -f "${errfile}"
    fail "${err:-current.json отклонён}" "${ACTION:-unknown}"
  fi
  rm -f "${errfile}"
  branch="$(printf '%s\n' "${meta}" | sed -n '1p')"
  sha="$(printf '%s\n' "${meta}" | sed -n '2p')"
  slot_id="$(printf '%s\n' "${meta}" | sed -n '3p')"
  version="$(printf '%s\n' "${meta}" | sed -n '4p')"
  [[ -n "${sha}" ]] || return 0
  if [[ -z "${branch}" ]]; then
    branch="unknown"
  fi
  if [[ -z "${slot_id}" ]]; then
    bsafe="$(printf '%s' "${branch}" | tr '/' '_')"
    slot_id="${bsafe}_${sha:0:12}"
    errfile="$(mktemp)"
    if ! slot_id="$(sanitize_field slot "${slot_id}" 2>"${errfile}")"; then
      err="$(head -n 1 "${errfile}" || true)"
      rm -f "${errfile}"
      fail "${err:-некорректный slot_id}" "${ACTION:-unknown}"
    fi
    rm -f "${errfile}"
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
  if [[ -d "${OPT_BAD}/panel" ]]; then
    rm -rf "${dest}/tree/panel"
    cp -a "${OPT_BAD}/panel" "${dest}/tree/panel"
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

download_tarball() {
  # Public: anonymous API / codeload / archive; private: нужен token.
  local repo="$1" sha="$2" out="$3" api="$4" token="$5"
  local ua="bad-apply-server-update/1.0"
  local api_url="${api%/}/repos/${repo}/tarball/${sha}"
  local codeload_url="https://codeload.github.com/${repo}/tar.gz/${sha}"
  local archive_url="https://github.com/${repo}/archive/${sha}.tar.gz"
  local curl_base=(-fsSL -o "${out}" -H "User-Agent: ${ua}")
  local hdr_api=(-H "Accept: application/vnd.github+json")
  if [[ -n "${token}" ]]; then
    hdr_api+=(-H "Authorization: Bearer ${token}")
  fi
  if curl "${curl_base[@]}" "${hdr_api[@]}" "${api_url}"; then
    return 0
  fi
  # Anonymous fallbacks (public repos; token не обязателен для check/apply)
  if curl "${curl_base[@]}" "${codeload_url}"; then
    return 0
  fi
  if curl "${curl_base[@]}" "${archive_url}"; then
    return 0
  fi
  return 1
}

download_and_fill_slot() {
  local branch sha repo api token slot_id dest tarball tmp bsafe errfile err list_rc
  errfile="$(mktemp)"
  if ! branch="$(sanitize_field branch "$1" 2>"${errfile}")"; then
    err="$(head -n 1 "${errfile}" || true)"
    rm -f "${errfile}"
    fail "${err:-некорректная ветка}" "apply"
  fi
  if ! sha="$(sanitize_field sha "$2" 2>"${errfile}")"; then
    err="$(head -n 1 "${errfile}" || true)"
    rm -f "${errfile}"
    fail "${err:-некорректный SHA}" "apply"
  fi
  rm -f "${errfile}"
  repo="$(read_site_env_var BAD_GITHUB_REPO "${BAD_GITHUB_REPO:-blazerity/bAD}")"
  api="$(read_site_env_var BAD_GITHUB_API_BASE "${BAD_GITHUB_API_BASE:-$API_BASE_DEFAULT}")"
  token="$(github_token)"
  [[ -n "${sha}" ]] || fail "SHA пуст для apply" "apply"
  bsafe="$(printf '%s' "${branch}" | tr '/' '_')"
  slot_id="${bsafe}_${sha:0:12}"
  errfile="$(mktemp)"
  if ! slot_id="$(sanitize_field slot "${slot_id}" 2>"${errfile}")"; then
    err="$(head -n 1 "${errfile}" || true)"
    rm -f "${errfile}"
    fail "${err:-некорректный slot_id}" "apply"
  fi
  rm -f "${errfile}"
  dest="${SLOTS}/${slot_id}"
  mkdir -p "${dest}/tree"
  tmp="$(mktemp -d)"
  tarball="${tmp}/src.tgz"
  if ! download_tarball "${repo}" "${sha}" "${tarball}" "${api}" "${token}"; then
    rm -rf "${tmp}"
    if [[ -z "${token}" ]]; then
      fail "не удалось скачать ${repo}@${sha:0:12} без token (API/codeload). Private repo — задайте BAD_GITHUB_TOKEN" "apply"
    fi
    fail "не удалось скачать tarball ${repo}@${sha:0:12}" "apply"
  fi
  mkdir -p "${tmp}/extract"
  set +e
  "${BAD_PYTHON}" - "${tarball}" <<'PY'
import subprocess, sys
tarball = sys.argv[1]
proc = subprocess.run(["tar", "-tzf", tarball], capture_output=True, text=True)
if proc.returncode != 0:
    sys.stderr.write(proc.stderr or "tar -tzf failed\n")
    raise SystemExit(1)
for name in proc.stdout.splitlines():
    if name.startswith("/") or ".." in name or "\\" in name:
        sys.stderr.write("unsafe archive name\n")
        raise SystemExit(2)
PY
  list_rc=$?
  set -e
  if [[ "${list_rc}" -ne 0 ]]; then
    rm -rf "${tmp}/extract" "${tmp}"
    if [[ "${list_rc}" -eq 2 ]]; then
      fail "небезопасное имя в архиве" "apply"
    fi
    fail "повреждённый tarball" "apply"
  fi
  if ! tar -xzf "${tarball}" -C "${tmp}/extract" --strip-components=1; then
    rm -rf "${tmp}/extract" "${tmp}"
    fail "повреждённый tarball" "apply"
  fi
  [[ -d "${tmp}/extract/server" ]] || { rm -rf "${tmp}"; fail "в архиве нет server/" "apply"; }
  [[ -d "${tmp}/extract/panel" ]] || { rm -rf "${tmp}"; fail "в архиве нет panel/" "apply"; }
  rm -rf "${dest}/tree/server" "${dest}/tree/panel" "${dest}/tree/deploy" "${dest}/tree/VERSION" "${dest}/tree/agent"
  cp -a "${tmp}/extract/server" "${dest}/tree/server"
  cp -a "${tmp}/extract/panel" "${dest}/tree/panel"
  if [[ -d "${tmp}/extract/deploy" ]]; then
    cp -a "${tmp}/extract/deploy" "${dest}/tree/deploy"
  fi
  # Корневой VERSION = server; agent/VERSION — отдельно (MSI line)
  if [[ -f "${tmp}/extract/VERSION" ]]; then
    cp -a "${tmp}/extract/VERSION" "${dest}/tree/VERSION"
  fi
  if [[ -f "${tmp}/extract/agent/VERSION" ]]; then
    mkdir -p "${dest}/tree/agent"
    cp -a "${tmp}/extract/agent/VERSION" "${dest}/tree/agent/VERSION"
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
  local slot_id source_label errfile err meta branch sha version
  source_label="$2"
  errfile="$(mktemp)"
  if ! slot_id="$(sanitize_field slot "$1" 2>"${errfile}")"; then
    err="$(head -n 1 "${errfile}" || true)"
    rm -f "${errfile}"
    fail "${err:-некорректный slot_id}" "${source_label}"
  fi
  rm -f "${errfile}"
  local dest="${SLOTS}/${slot_id}"
  [[ -d "${dest}/tree/server" ]] || fail "слот ${slot_id}: нет tree/server" "${source_label}"
  [[ -d "${dest}/tree/panel" ]] || fail "слот ${slot_id}: нет tree/panel" "${source_label}"
  mkdir -p "${OPT_BAD}"
  # Atomic-ish replace of server tree
  local new_server="${OPT_BAD}/.server.next"
  local bak_server="${OPT_BAD}/.server.bak"
  local new_panel="${OPT_BAD}/.panel.next"
  local bak_panel="${OPT_BAD}/.panel.bak"
  rm -rf "${new_server}" "${new_panel}"
  cp -a "${dest}/tree/server" "${new_server}"
  cp -a "${dest}/tree/panel" "${new_panel}"
  if [[ -d "${OPT_BAD}/server" ]]; then
    rm -rf "${bak_server}"
    mv "${OPT_BAD}/server" "${bak_server}"
  fi
  if [[ -d "${OPT_BAD}/panel" ]]; then
    rm -rf "${bak_panel}"
    mv "${OPT_BAD}/panel" "${bak_panel}"
  fi
  mv "${new_server}" "${OPT_BAD}/server"
  mv "${new_panel}" "${OPT_BAD}/panel"
  rm -rf "${bak_server}" "${bak_panel}"

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
  if [[ -f "${dest}/tree/agent/VERSION" ]]; then
    mkdir -p "${OPT_BAD}/agent"
    cp -a "${dest}/tree/agent/VERSION" "${OPT_BAD}/agent/VERSION"
    chown root:bad "${OPT_BAD}/agent" "${OPT_BAD}/agent/VERSION" 2>/dev/null || true
    chmod 755 "${OPT_BAD}/agent" 2>/dev/null || true
    chmod 644 "${OPT_BAD}/agent/VERSION" 2>/dev/null || true
  fi

  chown -R bad:bad "${OPT_BAD}/server" "${OPT_BAD}/panel" 2>/dev/null || true
  if [[ -d "${OPT_BAD}/.venv" ]]; then
    # Reinstall editable package into existing venv
    if ! "${OPT_BAD}/.venv/bin/pip" install -e "${OPT_BAD}/server" >/tmp/bad-server-update-pip.log 2>&1; then
      fail "pip install -e server не удался (см. /tmp/bad-server-update-pip.log)" "${source_label}"
    fi
  fi

  errfile="$(mktemp)"
  if ! meta="$(read_meta_fields "${dest}/meta.json" 2>"${errfile}")"; then
    err="$(head -n 1 "${errfile}" || true)"
    rm -f "${errfile}"
    fail "${err:-meta.json отклонён}" "${source_label}"
  fi
  rm -f "${errfile}"
  branch="$(printf '%s\n' "${meta}" | sed -n '1p')"
  sha="$(printf '%s\n' "${meta}" | sed -n '2p')"
  version="$(printf '%s\n' "${meta}" | sed -n '4p')"
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
init_bad_python

if [[ ! -f "${REQUEST}" ]]; then
  echo "bad-apply-server-update: no request, exit"
  exit 0
fi

errfile="$(mktemp)"
if ! req="$(read_request 2>"${errfile}")"; then
  err="$(head -n 1 "${errfile}" || true)"
  rm -f "${errfile}"
  fail "${err:-заявка отклонена}" "unknown"
fi
rm -f "${errfile}"
ACTION="$(printf '%s\n' "${req}" | sed -n '1p')"
BRANCH="$(printf '%s\n' "${req}" | sed -n '2p')"
SHA="$(printf '%s\n' "${req}" | sed -n '3p')"
SLOT_ID="$(printf '%s\n' "${req}" | sed -n '4p')"

case "${ACTION}" in
  set_token)
    set_token_in_site_env
    ;;
  apply)
    [[ -n "${BRANCH}" ]] || BRANCH="main"
    errfile="$(mktemp)"
    if ! BRANCH="$(sanitize_field branch "${BRANCH}" 2>"${errfile}")"; then
      err="$(head -n 1 "${errfile}" || true)"
      rm -f "${errfile}"
      fail "${err:-некорректная ветка}" "apply"
    fi
    rm -f "${errfile}"
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
    errfile="$(mktemp)"
    if ! SHA="$(sanitize_field sha "${SHA}" 2>"${errfile}")"; then
      err="$(head -n 1 "${errfile}" || true)"
      rm -f "${errfile}"
      fail "${err:-некорректный SHA}" "apply"
    fi
    rm -f "${errfile}"
    archive_current_slot
    SLOT_ID="$(download_and_fill_slot "${BRANCH}" "${SHA}")"
    promote_slot "${SLOT_ID}" "apply"
    prune_slots
    write_status true "Установлено ${BRANCH}@${SHA:0:12}; bad-api restart" "apply"
    restart_api
    ;;
  rollback)
    [[ -n "${SLOT_ID}" ]] || fail "slot_id обязателен для rollback" "rollback"
    errfile="$(mktemp)"
    if ! SLOT_ID="$(sanitize_field slot "${SLOT_ID}" 2>"${errfile}")"; then
      err="$(head -n 1 "${errfile}" || true)"
      rm -f "${errfile}"
      fail "${err:-некорректный slot_id}" "rollback"
    fi
    rm -f "${errfile}"
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
