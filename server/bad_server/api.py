from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from . import __version__
from .agent_config import (
    ALLOWED_SETTING_KEYS,
    CONDITION_FIELDS,
    CONDITION_OPS,
    CONFIG_SOURCES,
    DEFAULT_AGENT_SETTINGS,
    sanitize_settings,
)
from .agent_update import check_update, sync_from_github
from .auth import get_db, require_admin_token, require_api_key, require_enrollment_token
from .config import Settings, get_settings
from .crypto_util import decrypt_secret
from .db import Database
from .schemas import (
    AgentPolicyBody,
    DeviceConfigOverrideBody,
    DeviceTagsBody,
    EnrollRequest,
    EnrollResponse,
    HeartbeatRequest,
    InventoryRequest,
)
from .http_bootstrap import ENROLL_CLEARTEXT_MSG, enroll_cleartext_blocked
from .security import api_key_lookup, generate_token, hash_secret, verify_secret
from .inventory_events import sanitize_inventory_payload
from .smtp_mail import notify_enroll, notify_inventory_events

logger = logging.getLogger(__name__)

# Additive freeze /v1: новые optional поля и эндпоинты ок; breaking — только по решению владельца.
# Интеграционный гайд (1C Itilium и др.): docs/api-v1.md
router = APIRouter(prefix="/v1")

# SEC-001: enrollment token alone cannot un-revoke (api early path + DB TOCTOU guard).
_DEVICE_REVOKED_DETAIL = (
    "Device access revoked; admin must rotate API key in web UI "
    "(enrollment token alone cannot un-revoke)"
)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.post("/enroll", response_model=EnrollResponse)
def enroll(
    body: EnrollRequest,
    request: Request,
    _enrollment: str = Depends(require_enrollment_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EnrollResponse:
    if enroll_cleartext_blocked(request, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ENROLL_CLEARTEXT_MSG,
        )
    client = request.client.host if request.client else "unknown"
    limiter = request.app.state.enroll_limiter
    if not limiter.allow(client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Enrollment rate limit exceeded",
        )

    # SEC-001: enrollment token alone cannot un-revoke (early + DB TOCTOU guard).
    _REVOKED_DETAIL = (
        "Device access revoked; admin must rotate API key in web UI "
        "(enrollment token alone cannot un-revoke)"
    )

    existing = db.get_device_auth_row(body.device_id)
    allow_existing = False
    if existing:
        if existing.get("revoked"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_REVOKED_DETAIL,
            )
        # Re-key only with proof of current API key (SEC-001).
        proof = (body.current_api_key or "").strip()
        if not proof or not verify_secret(existing["api_key_hash"], proof):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Device already enrolled; re-enroll requires current_api_key "
                    "or admin rotate-key"
                ),
            )
        allow_existing = True

    api_key = generate_token("bad_ak_")
    api_key_hash = hash_secret(api_key)
    data_key = getattr(request.app.state, "data_key", "") or ""
    lookup = api_key_lookup(data_key, api_key) if data_key else None
    try:
        created = db.upsert_device_on_enroll(
            device_id=body.device_id,
            hostname=body.hostname,
            api_key_hash=api_key_hash,
            agent_version=body.agent_version,
            api_key_lookup=lookup,
            allow_existing=allow_existing,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "device_revoked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_REVOKED_DETAIL,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already enrolled",
        ) from exc
    if created:
        try:
            from .enrollment_ops import mark_device_enrolled

            mark_device_enrolled(db)
        except Exception:  # noqa: BLE001
            logger.exception("last_enrollment_at stamp failed (ignored)")
        try:
            smtp_row = db.get_smtp_settings()
            password = ""
            enc = smtp_row.get("password_enc") or ""
            if enc:
                data_key = getattr(request.app.state, "data_key", None)
                if data_key:
                    password = decrypt_secret(data_key, enc) or ""
            notify_enroll(
                smtp_row,
                password=password,
                device_id=body.device_id,
                hostname=body.hostname,
            )
        except Exception:  # noqa: BLE001
            logger.exception("SMTP enroll alert failed (ignored)")
    return EnrollResponse(api_key=api_key, device_id=body.device_id)


@router.post("/heartbeat")
def heartbeat(
    body: HeartbeatRequest,
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if body.device_id != device["device_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="device_id mismatch")
    # Omit/null config_local → keep previous; present (incl. keys:[]) → sanitize + store/clear.
    config_local_provided = body.config_local is not None
    config_local_payload = (
        body.config_local.sanitized() if body.config_local is not None else None
    )
    db.update_heartbeat(
        device_id=body.device_id,
        agent_version=body.agent_version,
        last_inventory_at=body.last_inventory_at,
        health={
            "last_inventory_ok": body.last_inventory_ok,
            "last_inventory_error": body.last_inventory_error,
            "agent_uptime_seconds": body.agent_uptime_seconds,
            "system_drive_free_bytes": body.system_drive_free_bytes,
        },
        config_local=config_local_payload,
        config_local_provided=config_local_provided,
    )
    effective = db.compute_device_effective_config(body.device_id)
    assert effective is not None
    resp: dict[str, Any] = {
        "status": "ok",
        "config_version": effective["version"],
    }
    # Подложить полный settings, если у агента ещё нет version или она изменилась.
    # config_local does not affect piggyback config / version.
    if not body.config_version or body.config_version != effective["version"]:
        resp["config"] = {
            "version": effective["version"],
            "settings": effective["settings"],
        }
    return resp


@router.get("/agent/config")
def agent_config(
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Enrolled-агент забирает свои эффективные remote settings (в рамках API key)."""
    effective = db.compute_device_effective_config(device["device_id"])
    assert effective is not None
    return {
        "device_id": device["device_id"],
        "version": effective["version"],
        "settings": effective["settings"],
    }


@router.post("/inventory")
def inventory(
    body: InventoryRequest,
    request: Request,
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if body.device_id != device["device_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="device_id mismatch")
    if body.schema_version not in settings.known_schema_versions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported schema_version: {body.schema_version}",
        )

    # Additive schema_version=2; strip dump bodies if agent ever sends them.
    payload = sanitize_inventory_payload(body.model_dump())
    hostname = None
    host = payload.get("host") if isinstance(payload.get("host"), dict) else None
    if host:
        hostname = host.get("hostname")
    os_meta: dict[str, Any] = {}
    if host and isinstance(host.get("os"), dict):
        os_meta["os"] = host["os"].get("caption")
    serial = None
    hardware = (
        payload.get("hardware")
        if isinstance(payload.get("hardware"), dict)
        else None
    )
    if hardware:
        serial = hardware.get("serial_number")
    meta = {
        "last_inventory_at": body.collected_at,
        **os_meta,
    }
    if serial:
        meta["serial_number"] = serial
    stored = db.store_inventory(
        device_id=body.device_id,
        schema_version=body.schema_version,
        payload=payload,
        hostname=hostname,
        agent_version=body.agent_version,
        meta=meta,
        retention=settings.snapshot_retention,
    )
    # Soft-fail SMTP: никогда не ломать приём inventory.
    try:
        smtp_row = db.get_smtp_settings()
        password = ""
        enc = smtp_row.get("password_enc") or ""
        if enc:
            data_key = getattr(request.app.state, "data_key", None)
            if data_key:
                password = decrypt_secret(data_key, enc) or ""
        notify_inventory_events(
            smtp_row,
            password=password,
            device_id=body.device_id,
            hostname=hostname or device["hostname"],
            events=stored.get("events") or [],
        )
    except Exception:  # noqa: BLE001
        logger.exception("SMTP hardware alert failed (ignored)")
    return {"status": "ok", "snapshot_id": stored["snapshot_id"]}


@router.get("/devices")
def list_devices(
    tag: str | None = Query(default=None, max_length=64),
    q: str | None = Query(default=None, max_length=128),
    archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    tag_filter = (tag or "").strip() or None
    query = (q or "").strip() or None
    total = db.count_devices(tag=tag_filter, archived=archived, q=query)
    offset = (page - 1) * page_size
    devices = db.list_devices(
        tag=tag_filter,
        archived=archived,
        q=query,
        offset=offset,
        limit=page_size,
    )
    return {
        "devices": devices,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/devices/{device_id}")
def get_device(
    device_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    detail = db.get_device_detail(device_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    detail["duplicates"] = db.find_duplicate_devices(device_id)
    return detail


@router.post("/devices/{device_id}/revoke")
def revoke_device(
    device_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.set_device_revoked(device_id, True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "device_id": device_id, "revoked": True}


@router.post("/devices/{device_id}/rotate-key")
def rotate_device_key(
    device_id: str,
    request: Request,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.get_device_detail(device_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    api_key = generate_token("bad_ak_")
    data_key = getattr(request.app.state, "data_key", "") or ""
    lookup = api_key_lookup(data_key, api_key) if data_key else None
    db.rotate_device_api_key(
        device_id, hash_secret(api_key), api_key_lookup=lookup
    )
    return {
        "status": "ok",
        "device_id": device_id,
        "api_key": api_key,
        "revoked": False,
    }


@router.post("/devices/{device_id}/archive")
def archive_device(
    device_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.set_device_archived(device_id, True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "device_id": device_id, "archived": True}


@router.post("/devices/{device_id}/restore")
def restore_device(
    device_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.set_device_archived(device_id, False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "device_id": device_id, "archived": False}


@router.delete("/devices/{device_id}")
def delete_device(
    device_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.delete_device(device_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "device_id": device_id, "deleted": True}


@router.get("/events")
def list_events(
    device_id: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    device_filter = (device_id or "").strip() or None
    return {
        "events": db.list_device_events(
            device_id=device_filter, limit=limit, offset=offset
        ),
        "total": db.count_device_events(device_id=device_filter),
        "limit": limit,
        "offset": offset,
    }


@router.put("/devices/{device_id}/tags")
def put_device_tags(
    device_id: str,
    body: DeviceTagsBody,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        saved = db.set_device_tags(device_id, body.tags)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        ) from exc
    return {"device_id": device_id, "tags": saved}


@router.get("/agent/update/check")
def agent_update_check(
    current: str = Query(default="", max_length=64),
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Агенты спрашивают, есть ли целевой MSI (effective update_target)."""
    return check_update(
        db,
        current=current or "0.0.0",
        device=dict(device) if device is not None else None,
    )


@router.get("/agent/update/msi")
def agent_update_msi(
    version: str = Query(default="", max_length=64),
    _device=Depends(require_api_key),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Скачать байты зеркалированного MSI (auth: API key агента)."""
    from .github_release import safe_msi_filename
    from .agent_update import resolve_target_msi

    ver = (version or "").strip()
    mirrored = (
        db.get_agent_msi_version(ver) if ver else None
    ) or resolve_target_msi(db, ver or "latest")
    if not mirrored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No agent update mirrored yet",
        )
    try:
        safe_name = safe_msi_filename(mirrored["msi_name"])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mirrored MSI name is unsafe",
        ) from exc
    path = Path(mirrored["file_path"]).resolve()
    updates_root = settings.agent_updates_dir.resolve()
    try:
        path.relative_to(updates_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mirrored MSI path escapes updates dir",
        ) from exc
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mirrored MSI file missing on disk",
        )
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=safe_name,
    )


@router.get("/admin/agent-update")
def admin_agent_update_status(
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    mirrored = db.get_agent_update()
    return {
        "github_repo": settings.github_repo,
        "updates_dir": str(settings.agent_updates_dir),
        "sync_interval_seconds": settings.agent_update_sync_interval_seconds,
        "mirrored": mirrored,
        "versions": db.list_agent_msi_versions(),
    }


@router.post("/admin/agent-update/sync")
def admin_agent_update_sync(
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    try:
        record = sync_from_github(db, settings)
    except Exception as exc:  # noqa: BLE001 — показать ошибки sync админу
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub sync failed: {exc}",
        ) from exc
    return {"status": "ok", "mirrored": record, "latest": db.get_agent_update()}


@router.post("/admin/agent-update/upload")
async def admin_agent_update_upload(
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    msi: UploadFile = File(...),
    version: str = Form(""),
    sha256: str = Form(""),
    set_latest: str = Form("true"),
    manifest: Optional[UploadFile] = File(None),
) -> dict[str, Any]:
    from .agent_update import ingest_uploaded_msi

    raw = await msi.read()
    manifest_text = None
    if manifest is not None and manifest.filename:
        manifest_text = (await manifest.read()).decode("utf-8")
    try:
        record = ingest_uploaded_msi(
            db,
            settings,
            raw=raw,
            filename=msi.filename or "",
            version=version,
            sha256=sha256,
            manifest_json=manifest_text,
            set_as_latest=str(set_latest).strip().lower()
            in {"1", "true", "yes", "on"},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {"status": "ok", "mirrored": record, "latest": db.get_agent_update()}


@router.post("/admin/agent-update/{version}/set-latest")
def admin_agent_update_set_latest(
    version: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    from .agent_update import set_latest_msi_version

    try:
        record = set_latest_msi_version(db, version)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return {"status": "ok", "latest": record}


@router.delete("/admin/agent-update/{version}")
def admin_agent_update_delete(
    version: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from .agent_update import delete_msi_version

    try:
        delete_msi_version(db, settings, version)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {"status": "ok", "deleted": version, "latest": db.get_agent_update()}


@router.get("/admin/server-update")
def admin_server_update_status(
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Статус self-update сервера (ветка, current, слоты ≤3, apply, token yes/no)."""
    from .server_update import status_panel

    return status_panel(settings)


@router.get("/admin/server-update/check")
def admin_server_update_check(
    branch: str = Query(default="", max_length=200),
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from .server_update import check_updates

    try:
        return check_updates(settings, branch=(branch or "").strip() or None)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/admin/server-update/branches")
def admin_server_update_branches(
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from .server_update import list_remote_branches

    try:
        names = list_remote_branches(settings)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return {"branches": names, "github_repo": settings.github_repo}


@router.post("/admin/server-update/branch")
def admin_server_update_set_branch(
    branch: str = Query(..., max_length=200),
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from .server_update import releases_dir, set_preferred_branch

    try:
        prefs = set_preferred_branch(branch, releases_dir(settings))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {"status": "ok", "prefs": prefs}


def _admin_server_update_request(
    settings: Settings,
    *,
    wait: bool,
    timeout_seconds: float = 180.0,
    **apply_kwargs: Any,
) -> dict[str, Any]:
    """Записать apply.request (+ опц. дождаться status). Общий путь apply/rollback."""
    from .server_update import releases_dir, request_apply, wait_for_apply

    root = releases_dir(settings)
    try:
        req = request_apply(directory=root, **apply_kwargs)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    apply = (
        wait_for_apply(
            root,
            since=str(req.get("requested_at") or ""),
            timeout_seconds=timeout_seconds,
        )
        if wait
        else None
    )
    return {"status": "ok", "request": req, "apply": apply}


@router.post("/admin/server-update/apply")
def admin_server_update_apply(
    branch: str = Query(default="", max_length=200),
    sha: str = Query(default="", max_length=40),
    wait: bool = Query(default=True),
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Запросить apply через systemd path helper (+ опц. дождаться status)."""
    return _admin_server_update_request(
        settings, wait=wait, action="apply", branch=branch, sha=sha
    )


@router.post("/admin/server-update/rollback")
def admin_server_update_rollback(
    slot_id: str = Query(..., max_length=120),
    wait: bool = Query(default=True),
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _admin_server_update_request(
        settings, wait=wait, action="rollback", slot_id=slot_id
    )


@router.get("/admin/server-update/apply-status")
def admin_server_update_apply_status(
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from .server_update import read_apply_status, releases_dir

    return read_apply_status(releases_dir(settings))


@router.post("/admin/server-update/token")
def admin_server_update_set_token(
    token: str = Form(...),
    wait: bool = Form(True),
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Записать GH token через helper в site.env. Ответ без plaintext."""
    from .server_update import (
        releases_dir,
        request_set_github_token,
        token_configured,
        wait_for_apply,
    )

    root = releases_dir(settings)
    try:
        req = request_set_github_token(token, directory=root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    apply = (
        wait_for_apply(root, since=str(req.get("requested_at") or ""), timeout_seconds=30.0)
        if wait
        else None
    )
    # Сбросить кэш Settings после записи env (новый процесс после restart;
    # set_token не рестартит API — токен подхватится при следующем старте /
    # если уже был в env process — UI покажет configured после helper + file).
    get_settings.cache_clear()
    return {
        "status": "ok",
        "token_configured": token_configured(get_settings()),
        "apply": apply,
    }


@router.post("/admin/server-update/msi/trigger")
def admin_server_update_msi_trigger(
    branch: str = Query(default="", max_length=200),
    version: str = Query(default="", max_length=64),
    _admin: str = Depends(require_admin_token),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from .server_update import trigger_msi_workflow

    try:
        meta = trigger_msi_workflow(
            settings,
            branch=(branch or "").strip() or None,
            version=version,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return {"status": "ok", "msi_build": meta}


@router.post("/admin/server-update/msi/poll")
def admin_server_update_msi_poll(
    ingest: bool = Query(default=True),
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from .server_update import poll_msi_workflow

    try:
        meta = poll_msi_workflow(settings, ingest=ingest, db=db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return {"status": "ok", "msi_build": meta}


@router.post("/admin/enrollment/rotate")
def admin_enrollment_rotate(
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    token: str = Query(default="", max_length=256),
) -> dict[str, Any]:
    """Сменить enrollment token. Plaintext в ответе один раз; query token= — свой."""
    from .enrollment_ops import rotate_enrollment_token

    result = rotate_enrollment_token(
        db, settings, new_token=(token or "").strip() or None
    )
    return {
        "status": "ok",
        "token": result["token"],
        "rotated_at": result.get("rotated_at"),
        "wrote_token_file": result.get("wrote_token_file"),
        "updated_site_env": result.get("updated_site_env"),
    }


@router.get("/admin/security-status")
def admin_security_status(
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Theme A: HTTPS-first + SEC-005 + enrollment rotation hooks (no plaintext secrets)."""
    from .security_ops import security_status

    return security_status(db, settings)


@router.get("/admin/agent-config/defaults")
def admin_agent_config_defaults(
    _admin: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Allowlist knobs + condition fields (тема C) для UI/интеграторов."""
    return {
        "settings": dict(DEFAULT_AGENT_SETTINGS),
        "allowed_setting_keys": sorted(ALLOWED_SETTING_KEYS),
        "condition_fields": sorted(CONDITION_FIELDS),
        "condition_ops": sorted(CONDITION_OPS),
        "config_sources": sorted(CONFIG_SOURCES),
        "remote_merge": "defaults < matching policies (priority asc) < device_override",
        "ui_provenance_order": "agent_local > device_override > policy > default",
    }


@router.get("/admin/policies")
def admin_list_policies(
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    return {"policies": db.list_agent_policies()}


@router.post("/admin/policies", status_code=status.HTTP_201_CREATED)
def admin_create_policy(
    body: AgentPolicyBody,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    policy = db.create_agent_policy(
        name=body.name.strip(),
        enabled=body.enabled,
        priority=body.priority,
        conditions=[c.model_dump() for c in body.conditions],
        settings=body.settings,
    )
    return {"policy": policy}


@router.get("/admin/policies/{policy_id}")
def admin_get_policy(
    policy_id: int,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    policy = db.get_agent_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return {"policy": policy}


@router.put("/admin/policies/{policy_id}")
def admin_update_policy(
    policy_id: int,
    body: AgentPolicyBody,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    policy = db.update_agent_policy(
        policy_id,
        name=body.name.strip(),
        enabled=body.enabled,
        priority=body.priority,
        conditions=[c.model_dump() for c in body.conditions],
        settings=body.settings,
    )
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return {"policy": policy}


@router.delete("/admin/policies/{policy_id}")
def admin_delete_policy(
    policy_id: int,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, str]:
    if not db.delete_agent_policy(policy_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return {"status": "ok"}


@router.get("/admin/devices/{device_id}/config")
def admin_device_config(
    device_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    effective = db.compute_device_effective_config(device_id)
    if not effective:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {
        "device_id": device_id,
        "defaults": dict(DEFAULT_AGENT_SETTINGS),
        "allowed_setting_keys": sorted(ALLOWED_SETTING_KEYS),
        "effective": effective["settings"],
        "version": effective["version"],
        "matched_policies": effective["matched_policies"],
        "policy_keys": effective.get("policy_keys") or [],
        "override_keys": effective.get("override_keys") or [],
        "context": effective["context"],
        "override": effective.get("override"),
        "has_override": effective["has_override"],
        "sources": effective.get("sources") or {},
        "agent_local_keys": effective.get("agent_local_keys") or [],
        "has_agent_local": bool(effective.get("has_agent_local")),
        "config_local": effective.get("config_local"),
    }


@router.put("/admin/devices/{device_id}/config-override")
def admin_set_device_override(
    device_id: str,
    body: DeviceConfigOverrideBody,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    cleaned = sanitize_settings(body.settings)
    try:
        override = db.set_device_config_override(device_id, cleaned)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        ) from exc
    effective = db.compute_device_effective_config(device_id)
    assert effective is not None
    return {
        "override": override,
        "effective": effective["settings"],
        "version": effective["version"],
    }


@router.delete("/admin/devices/{device_id}/config-override")
def admin_delete_device_override(
    device_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    detail = db.get_device_detail(device_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    db.delete_device_config_override(device_id)
    effective = db.compute_device_effective_config(device_id)
    assert effective is not None
    return {
        "status": "ok",
        "effective": effective["settings"],
        "version": effective["version"],
    }

