from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from . import __version__
from .agent_config import DEFAULT_AGENT_SETTINGS, sanitize_settings
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
from .security import api_key_lookup, generate_token, hash_secret, verify_secret
from .smtp_mail import notify_enroll, notify_inventory_events

logger = logging.getLogger(__name__)

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
    )
    effective = db.compute_device_effective_config(body.device_id)
    assert effective is not None
    resp: dict[str, Any] = {
        "status": "ok",
        "config_version": effective["version"],
    }
    # Подложить полный settings, если у агента ещё нет version или она изменилась.
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

    payload = body.model_dump()
    hostname = None
    if body.host and isinstance(body.host, dict):
        hostname = body.host.get("hostname")
    os_meta: dict[str, Any] = {}
    if body.host and isinstance(body.host.get("os"), dict):
        os_meta["os"] = body.host["os"].get("caption")
    serial = None
    if body.hardware and isinstance(body.hardware, dict):
        serial = body.hardware.get("serial_number")
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
    update_target: str = Query(default="", max_length=64),
    desired: str = Query(default="", max_length=64),
    _device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Агенты спрашивают целевой MSI (0.10). Target: query hint или later effective config."""
    target = (update_target or desired or "latest").strip() or "latest"
    return check_update(
        db,
        current=current or "0.0.0",
        update_target=target,
        desired=target,
    )


@router.get("/agent/update/msi")
def agent_update_msi(
    _device=Depends(require_api_key),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Скачать байты зеркалированного MSI (auth: API key агента)."""
    from .github_release import safe_msi_filename

    mirrored = db.get_agent_update()
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
    return {"status": "ok", "mirrored": record}


@router.get("/admin/agent-config/defaults")
def admin_agent_config_defaults(
    _admin: str = Depends(require_admin_token),
) -> dict[str, Any]:
    return {"settings": dict(DEFAULT_AGENT_SETTINGS)}


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
        "effective": effective["settings"],
        "version": effective["version"],
        "matched_policies": effective["matched_policies"],
        "context": effective["context"],
        "override": effective.get("override"),
        "has_override": effective["has_override"],
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

