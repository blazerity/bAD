"""Обновление сервера (панель/API) из GitHub: check / apply / rollback / MSI trigger.

Apply идёт через privileged helper (systemd path), как TLS — не sudo-password в UI.
Зеркало MSI агента (`agent_update`) — отдельно; здесь только self-update + опц. Actions.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

from .config import Settings
from .db import utc_now

logger = logging.getLogger(__name__)

DEFAULT_RELEASES_DIR = Path("/var/lib/bad/server-releases")
DEFAULT_BRANCH = "main"
MAX_PAST_SLOTS = 3
APPLY_REQUEST = "apply.request"
APPLY_STATUS = "apply.status"
CURRENT_META = "current.json"
PREFS_META = "prefs.json"
SLOTS_DIRNAME = "slots"
STAGING_DIRNAME = "staging"
TOKEN_STAGING = "github_token.staging"
MSI_WORKFLOW = "release-msi.yml"
MSI_JOB_META = "msi_build.json"

_BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_SLOT_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def releases_dir(settings: Optional[Settings] = None) -> Path:
    if settings is not None and getattr(settings, "server_releases_dir", None):
        return Path(settings.server_releases_dir)
    raw = os.environ.get("BAD_SERVER_RELEASES_DIR", "").strip()
    return Path(raw) if raw else DEFAULT_RELEASES_DIR


def apply_request_path(directory: Optional[Path] = None) -> Path:
    return (directory or DEFAULT_RELEASES_DIR) / APPLY_REQUEST


def apply_status_path(directory: Optional[Path] = None) -> Path:
    return (directory or DEFAULT_RELEASES_DIR) / APPLY_STATUS


def current_meta_path(directory: Optional[Path] = None) -> Path:
    return (directory or DEFAULT_RELEASES_DIR) / CURRENT_META


def prefs_path(directory: Optional[Path] = None) -> Path:
    return (directory or DEFAULT_RELEASES_DIR) / PREFS_META


def slots_dir(directory: Optional[Path] = None) -> Path:
    return (directory or DEFAULT_RELEASES_DIR) / SLOTS_DIRNAME


def staging_dir(directory: Optional[Path] = None) -> Path:
    return (directory or DEFAULT_RELEASES_DIR) / STAGING_DIRNAME


def sanitize_branch(branch: str) -> str:
    value = (branch or "").strip()
    if not value:
        raise ValueError("Ветка не задана")
    if ".." in value or value.startswith("/") or value.endswith("/"):
        raise ValueError(f"Некорректная ветка: {branch!r}")
    if not _BRANCH_RE.match(value):
        raise ValueError(f"Некорректная ветка: {branch!r}")
    return value


def sanitize_sha(sha: str) -> str:
    value = (sha or "").strip().lower()
    if not value:
        raise ValueError("SHA не задан")
    if not _SHA_RE.match(value):
        raise ValueError(f"Некорректный SHA: {sha!r}")
    return value


def sanitize_slot_id(slot_id: str) -> str:
    value = (slot_id or "").strip()
    if not value or not _SLOT_RE.match(value):
        raise ValueError(f"Некорректный slot_id: {slot_id!r}")
    return value


def slot_id_for(branch: str, sha: str) -> str:
    b = sanitize_branch(branch).replace("/", "_")
    s = sanitize_sha(sha)[:12]
    return f"{b}_{s}"


def github_token(settings: Settings) -> str:
    """Токен из env/settings или из файла; plaintext наружу не отдавать."""
    tok = (settings.github_token or "").strip()
    if tok:
        return tok
    path = getattr(settings, "github_token_file", None)
    if path:
        p = Path(path)
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8").strip()
            except OSError:
                pass
    file_env = os.environ.get("BAD_GITHUB_TOKEN_FILE", "").strip()
    if file_env:
        p = Path(file_env)
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8").strip()
            except OSError:
                pass
    return ""


def token_configured(settings: Settings) -> bool:
    return bool(github_token(settings))


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _write_json(path: Path, data: dict[str, Any], *, mode: int = 0o640) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        tmp.chmod(mode)
    except OSError:
        pass
    tmp.replace(path)


def ensure_releases_layout(directory: Optional[Path] = None) -> Path:
    root = directory or DEFAULT_RELEASES_DIR
    root.mkdir(parents=True, exist_ok=True)
    slots_dir(root).mkdir(parents=True, exist_ok=True)
    staging_dir(root).mkdir(parents=True, exist_ok=True)
    try:
        root.chmod(0o770)
        # slots: 750 — process bad read-only; write только root helper
        slots_dir(root).chmod(0o750)
        staging_dir(root).chmod(0o770)
    except OSError:
        pass
    return root


def read_prefs(directory: Optional[Path] = None) -> dict[str, Any]:
    data = _read_json(prefs_path(directory)) or {}
    branch = str(data.get("branch") or DEFAULT_BRANCH).strip() or DEFAULT_BRANCH
    try:
        branch = sanitize_branch(branch)
    except ValueError:
        branch = DEFAULT_BRANCH
    return {"branch": branch}


def set_preferred_branch(
    branch: str, directory: Optional[Path] = None
) -> dict[str, Any]:
    ensure_releases_layout(directory)
    b = sanitize_branch(branch)
    prefs = {"branch": b, "updated_at": utc_now()}
    _write_json(prefs_path(directory), prefs)
    return prefs


def read_current(directory: Optional[Path] = None) -> dict[str, Any]:
    data = _read_json(current_meta_path(directory))
    if data:
        return data
    version = _read_installed_version()
    return {
        "branch": None,
        "sha": None,
        "version": version,
        "installed_at": None,
        "source": None,
        "slot_id": None,
        "unknown": True,
    }


def _read_installed_version() -> Optional[str]:
    for candidate in (
        Path("/opt/bad/VERSION"),
        Path(__file__).resolve().parents[2] / "VERSION",
        Path(__file__).resolve().parents[3] / "VERSION",
    ):
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8").strip()
                if text:
                    return text.splitlines()[0].strip()
            except OSError:
                continue
    try:
        from . import __version__

        return str(__version__)
    except Exception:  # noqa: BLE001
        return None


def list_rollback_slots(directory: Optional[Path] = None) -> list[dict[str, Any]]:
    """Прошлые слоты (не текущий), новые первые; ≤ MAX_PAST_SLOTS в UI."""
    root = directory or DEFAULT_RELEASES_DIR
    current = read_current(root)
    current_id = str(current.get("slot_id") or "")
    base = slots_dir(root)
    if not base.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for child in base.iterdir():
        if not child.is_dir():
            continue
        meta = _read_json(child / "meta.json") or {}
        slot_id = str(meta.get("slot_id") or child.name)
        if slot_id == current_id:
            continue
        items.append(
            {
                "slot_id": slot_id,
                "branch": meta.get("branch"),
                "sha": meta.get("sha"),
                "version": meta.get("version"),
                "installed_at": meta.get("installed_at"),
                "source": meta.get("source"),
            }
        )
    items.sort(key=lambda m: str(m.get("installed_at") or ""), reverse=True)
    return items[:MAX_PAST_SLOTS]


def read_apply_status(directory: Optional[Path] = None) -> dict[str, Any]:
    path = apply_status_path(directory)
    data = _read_json(path)
    if not data:
        return {
            "ok": None,
            "message": "apply ещё не выполнялся",
            "action": None,
            "applied_at": None,
        }
    return data


def wait_for_apply(
    directory: Optional[Path] = None,
    *,
    since: str = "",
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    deadline = time.time() + max(1.0, timeout_seconds)
    while time.time() < deadline:
        st = read_apply_status(directory)
        applied = str(st.get("applied_at") or "")
        if applied and (not since or applied >= since):
            if st.get("ok") is not None:
                return st
        time.sleep(0.5)
    return read_apply_status(directory)


def _gh_request(
    url: str,
    *,
    token: str = "",
    method: str = "GET",
    body: Optional[dict[str, Any]] = None,
    accept: str = "application/vnd.github+json",
    timeout: float = 60.0,
) -> Any:
    data = None
    headers = {
        "Accept": accept,
        "User-Agent": "bad-server-self-update/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_body = resp.read()
            if not raw_body:
                return None
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "json" in ctype or raw_body[:1] in (b"{", b"["):
                return json.loads(raw_body.decode("utf-8"))
            return raw_body
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API {exc.code}: {err_body[:400]}"
        ) from exc


def resolve_branch_head(
    settings: Settings, branch: str
) -> dict[str, Any]:
    b = sanitize_branch(branch)
    if not settings.github_repo:
        raise RuntimeError("BAD_GITHUB_REPO не задан")
    api = settings.github_api_base.rstrip("/")
    token = github_token(settings)
    url = (
        f"{api}/repos/{settings.github_repo}/commits/"
        f"{urllib.parse.quote(b, safe='')}"
    )
    data = _gh_request(url, token=token)
    if not isinstance(data, dict):
        raise RuntimeError("Неожиданный ответ GitHub commits")
    sha = str(data.get("sha") or "")
    if not sha:
        raise RuntimeError("GitHub не вернул SHA коммита")
    commit = data.get("commit") or {}
    message = ""
    if isinstance(commit, dict):
        message = str(commit.get("message") or "").splitlines()[0][:200]
    return {
        "branch": b,
        "sha": sha,
        "short_sha": sha[:12],
        "message": message,
        "html_url": data.get("html_url"),
    }


def list_remote_branches(settings: Settings, *, limit: int = 50) -> list[str]:
    if not settings.github_repo:
        raise RuntimeError("BAD_GITHUB_REPO не задан")
    api = settings.github_api_base.rstrip("/")
    token = github_token(settings)
    url = f"{api}/repos/{settings.github_repo}/branches?per_page={max(1, min(100, limit))}"
    data = _gh_request(url, token=token)
    if not isinstance(data, list):
        raise RuntimeError("Неожиданный ответ GitHub branches")
    names: list[str] = []
    for item in data:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return names


def check_updates(
    settings: Settings,
    *,
    branch: Optional[str] = None,
    directory: Optional[Path] = None,
) -> dict[str, Any]:
    """Сравнить установленный ref с HEAD выбранной ветки."""
    root = releases_dir(settings) if directory is None else directory
    prefs = read_prefs(root)
    b = sanitize_branch(branch or prefs.get("branch") or DEFAULT_BRANCH)
    current = read_current(root)
    error = None
    remote: Optional[dict[str, Any]] = None
    try:
        remote = resolve_branch_head(settings, b)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        logger.warning("server update check failed: %s", exc)

    current_sha = (current.get("sha") or "") or None
    remote_sha = (remote or {}).get("sha") if remote else None
    update_available = bool(
        remote_sha and (not current_sha or str(current_sha).lower() != str(remote_sha).lower())
    )
    return {
        "branch": b,
        "current": {
            "branch": current.get("branch"),
            "sha": current_sha,
            "short_sha": (current_sha or "")[:12] or None,
            "version": current.get("version") or _read_installed_version(),
            "installed_at": current.get("installed_at"),
            "slot_id": current.get("slot_id"),
            "unknown": bool(current.get("unknown")),
        },
        "remote": remote,
        "update_available": update_available if remote else False,
        "error": error,
        "github_repo": settings.github_repo,
        "token_configured": token_configured(settings),
    }


def request_apply(
    *,
    action: str,
    branch: str = "",
    sha: str = "",
    slot_id: str = "",
    directory: Optional[Path] = None,
) -> dict[str, Any]:
    """Записать apply.request для path unit (root helper)."""
    root = ensure_releases_layout(directory)
    act = (action or "").strip().lower()
    if act not in {"apply", "rollback"}:
        raise ValueError("action: apply|rollback")

    payload: dict[str, Any] = {
        "requested_at": utc_now(),
        "action": act,
    }
    if act == "apply":
        b = sanitize_branch(branch or read_prefs(root).get("branch") or DEFAULT_BRANCH)
        payload["branch"] = b
        if sha:
            payload["sha"] = sanitize_sha(sha)
        set_preferred_branch(b, root)
    else:
        payload["slot_id"] = sanitize_slot_id(slot_id)

    path = apply_request_path(root)
    _write_json(path, payload)
    logger.info(
        "server update requested action=%s branch=%s sha=%s slot=%s",
        act,
        payload.get("branch"),
        (payload.get("sha") or "")[:12],
        payload.get("slot_id"),
    )
    return payload


def request_set_github_token(
    token: str,
    *,
    directory: Optional[Path] = None,
) -> dict[str, Any]:
    """Положить токен в staging + apply.request action=set_token (helper → site.env)."""
    value = (token or "").strip()
    if not value:
        raise ValueError("Токен пуст")
    if any(ch in value for ch in "\r\n\0"):
        raise ValueError("Токен содержит недопустимые символы")
    root = ensure_releases_layout(directory)
    stage = staging_dir(root)
    tok_path = stage / TOKEN_STAGING
    tok_path.write_text(value + "\n", encoding="utf-8")
    try:
        tok_path.chmod(0o600)
    except OSError:
        pass
    payload = {
        "requested_at": utc_now(),
        "action": "set_token",
    }
    _write_json(apply_request_path(root), payload)
    return {"requested_at": payload["requested_at"], "action": "set_token"}


def status_panel(
    settings: Settings,
    *,
    directory: Optional[Path] = None,
) -> dict[str, Any]:
    root = releases_dir(settings) if directory is None else directory
    prefs = read_prefs(root)
    return {
        "prefs": prefs,
        "current": read_current(root),
        "slots": list_rollback_slots(root),
        "apply": read_apply_status(root),
        "token_configured": token_configured(settings),
        "github_repo": settings.github_repo,
        "releases_dir": str(root),
        "helper": {
            "unit": "bad-server-update-apply.service",
            "path_unit": "bad-server-update-apply.path",
            "script": "/usr/local/sbin/bad-apply-server-update",
            "mode": "systemd-path",
        },
        "msi_build": _read_json(root / MSI_JOB_META),
        "max_past_slots": MAX_PAST_SLOTS,
        "default_branch": DEFAULT_BRANCH,
    }


def trigger_msi_workflow(
    settings: Settings,
    *,
    branch: Optional[str] = None,
    version: str = "",
    publish_release: bool = True,
    directory: Optional[Path] = None,
) -> dict[str, Any]:
    """workflow_dispatch release-msi на выбранной ветке."""
    if not settings.github_repo:
        raise RuntimeError("BAD_GITHUB_REPO не задан")
    token = github_token(settings)
    if not token:
        raise RuntimeError(
            "Нужен BAD_GITHUB_TOKEN с правом actions:write для запуска workflow"
        )
    root = releases_dir(settings) if directory is None else directory
    ensure_releases_layout(root)
    b = sanitize_branch(branch or read_prefs(root).get("branch") or DEFAULT_BRANCH)
    api = settings.github_api_base.rstrip("/")
    url = (
        f"{api}/repos/{settings.github_repo}/actions/workflows/"
        f"{MSI_WORKFLOW}/dispatches"
    )
    inputs: dict[str, Any] = {
        "publish_release": "true" if publish_release else "false",
    }
    if (version or "").strip():
        inputs["version"] = version.strip().lstrip("vV")
    _gh_request(
        url,
        token=token,
        method="POST",
        body={"ref": b, "inputs": inputs},
    )
    meta = {
        "triggered_at": utc_now(),
        "branch": b,
        "workflow": MSI_WORKFLOW,
        "inputs": inputs,
        "status": "queued",
        "run_id": None,
        "conclusion": None,
        "html_url": None,
        "error": None,
        "ingested": None,
    }
    _write_json(root / MSI_JOB_META, meta)
    return meta


def poll_msi_workflow(
    settings: Settings,
    *,
    directory: Optional[Path] = None,
    ingest: bool = True,
    db: Any = None,
) -> dict[str, Any]:
    """Обновить статус последнего dispatch; при success опц. sync MSI в зеркало."""
    if not settings.github_repo:
        raise RuntimeError("BAD_GITHUB_REPO не задан")
    token = github_token(settings)
    root = releases_dir(settings) if directory is None else directory
    meta = _read_json(root / MSI_JOB_META) or {}
    branch = str(meta.get("branch") or read_prefs(root).get("branch") or DEFAULT_BRANCH)
    api = settings.github_api_base.rstrip("/")
    url = (
        f"{api}/repos/{settings.github_repo}/actions/workflows/"
        f"{MSI_WORKFLOW}/runs?branch={urllib.parse.quote(branch)}"
        f"&event=workflow_dispatch&per_page=5"
    )
    data = _gh_request(url, token=token)
    runs = (data or {}).get("workflow_runs") if isinstance(data, dict) else None
    if not isinstance(runs, list) or not runs:
        meta["status"] = meta.get("status") or "queued"
        meta["error"] = None
        _write_json(root / MSI_JOB_META, meta)
        return meta

    triggered = str(meta.get("triggered_at") or "")
    chosen = None
    for run in runs:
        if not isinstance(run, dict):
            continue
        created = str(run.get("created_at") or "")
        if triggered and created and created < triggered:
            continue
        chosen = run
        break
    if chosen is None:
        chosen = runs[0] if isinstance(runs[0], dict) else None
    if not chosen:
        return meta

    meta["run_id"] = chosen.get("id")
    meta["status"] = chosen.get("status")
    meta["conclusion"] = chosen.get("conclusion")
    meta["html_url"] = chosen.get("html_url")
    meta["error"] = None

    if (
        ingest
        and chosen.get("status") == "completed"
        and chosen.get("conclusion") == "success"
        and not meta.get("ingested")
        and db is not None
    ):
        try:
            from .agent_update import sync_from_github

            record = sync_from_github(db, settings)
            meta["ingested"] = {
                "version": record.get("version"),
                "msi_name": record.get("msi_name"),
                "sha256": record.get("sha256"),
                "at": utc_now(),
            }
        except Exception as exc:  # noqa: BLE001
            meta["error"] = f"Сборка OK, ingest зеркала: {exc}"
            logger.warning("MSI ingest after Actions failed: %s", exc)

    _write_json(root / MSI_JOB_META, meta)
    return meta
