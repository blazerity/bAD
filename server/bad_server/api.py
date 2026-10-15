from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .auth import get_db, require_admin_token, require_api_key, require_enrollment_token
from .config import Settings, get_settings
from .db import Database
from .schemas import EnrollRequest, EnrollResponse, HeartbeatRequest, InventoryRequest
from .security import generate_token, hash_secret

router = APIRouter(prefix="/v1")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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

    api_key = generate_token("bad_ak_")
    api_key_hash = hash_secret(api_key)
    db.upsert_device_on_enroll(
        device_id=body.device_id,
        hostname=body.hostname,
        api_key_hash=api_key_hash,
        agent_version=body.agent_version,
    )
    return EnrollResponse(api_key=api_key, device_id=body.device_id)


@router.post("/heartbeat")
def heartbeat(
    body: HeartbeatRequest,
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, str]:
    if body.device_id != device["device_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="device_id mismatch")
    db.update_heartbeat(
        device_id=body.device_id,
        agent_version=body.agent_version,
        last_inventory_at=body.last_inventory_at,
    )
    return {"status": "ok"}


@router.post("/inventory")
def inventory(
    body: InventoryRequest,
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
    meta = {
        "last_inventory_at": body.collected_at,
        **os_meta,
    }
    snapshot_id = db.store_inventory(
        device_id=body.device_id,
        schema_version=body.schema_version,
        payload=payload,
        hostname=hostname,
        agent_version=body.agent_version,
        meta=meta,
        retention=settings.snapshot_retention,
    )
    return {"status": "ok", "snapshot_id": snapshot_id}


@router.get("/devices")
def list_devices(
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    return {"devices": db.list_devices()}


@router.get("/devices/{device_id}")
def get_device(
    device_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    detail = db.get_device_detail(device_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return detail
