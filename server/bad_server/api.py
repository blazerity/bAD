from __future__ import annotations

import base64
import hashlib
import logging
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, HTMLResponse, Response

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
from .auth import (
    get_db,
    require_admin_token,
    require_api_key,
)
from .integrations import require_device_reader as _device_reader
from .device_refresh import (
    heartbeat_actions_for_refresh,
    heartbeat_refresh_meta_patch,
    refresh_request_pending,
    set_device_refresh_request,
)
from .device_uninstall import (
    expire_uninstall_request_if_needed,
    heartbeat_should_send_uninstall,
    mark_uninstall_sent_patch,
)
from pydantic import BaseModel

from .config import Settings, get_settings
from .db import Database
from .schemas import (
    AgentPolicyBody,
    DeviceConfigOverrideBody,
    DeviceTagsBody,
    EnrollRequest,
    EnrollResponse,
    EnrollmentGrantBody,
    EnrollmentRequestBody,
    HeartbeatRequest,
    IntegrationLookupBody,
    IntegrationRequestBody,
    InventoryRequest,
)
from .bad_id import is_bad_id
from .http_bootstrap import ENROLL_CLEARTEXT_MSG, client_ip, enroll_cleartext_blocked
from .crypto_util import decrypt_secret
from .security import (
    api_key_lookup,
    enrollment_code_hash,
    extract_bearer,
    generate_token,
    hash_secret,
    inventory_signing_bytes,
    new_device_signing_key,
    verify_inventory_signature,
    verify_secret,
)
from .device_meta import inventory_meta_cache
from .inventory_events import (
    INVENTORY_TOP_KEYS,
    inventory_budget_error,
    sanitize_inventory_payload,
)
from .smtp_mail import notify_enroll

logger = logging.getLogger(__name__)

# Additive freeze /v1: новые optional поля и эндпоинты ок; breaking — только по решению владельца.
router = APIRouter(prefix="/v1")

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.post("/enrollment-grants")
def create_enrollment_grant(
    body: EnrollmentGrantBody,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, str]:
    """Заявка админа: одноразовый код, привязанный к bad_id. Второй enroll — отказ."""
    code = generate_token("bad_ot_")
    db.create_enrollment_grant(body.bad_id, enrollment_code_hash(code))
    return {"code": code, "bad_id": body.bad_id}


def _enforce_enroll_rate(request: Request) -> None:
    if not request.app.state.enroll_limiter.allow(client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Enrollment rate limit exceeded",
        )


_SERIAL_PLACEHOLDERS = {
    "none",
    "n/a",
    "na",
    "default string",
    "system serial number",
    "to be filled by o.e.m.",
    "o.e.m.",
    "oem",
    "unknown",
    "not specified",
    "not available",
    "0",
}


def _enrollment_proof_bytes(text: str) -> bytes:
    """32 байта файла. Другая длина и не-base64 — 400. В журнал не пишется."""
    try:
        raw = base64.b64decode((text or "").strip(), validate=True)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="proof")
    if len(raw) != 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="proof")
    return raw


def _display_serial(serial: str) -> str:
    """Серийник только для панели. Заглушка BIOS не идентифицирует заявку."""
    text = serial.strip()
    if not text:
        return ""
    lower = text.casefold()
    if lower in _SERIAL_PLACEHOLDERS or lower.startswith("to be filled"):
        return ""
    compact = "".join(ch for ch in lower if ch not in "-_. ")
    if compact and (set(compact) <= {"0"} or set(compact) <= {"f"}):
        return ""
    return text


@router.post("/enrollment-requests")
def submit_enrollment_request(
    body: EnrollmentRequestBody,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Заявка без токена. Секрет забирает только опрос с тем же файлом proof."""
    _enforce_enroll_rate(request)
    proof_sha256 = hashlib.sha256(_enrollment_proof_bytes(body.proof)).hexdigest()
    hostname = body.hostname.strip()
    ip = (body.ip or "").strip()
    serial = _display_serial(body.serial or "")
    raw_bad_id = (body.bad_id or "").strip()
    if raw_bad_id and not is_bad_id(raw_bad_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad_id")
    bad_id = raw_bad_id
    guid = body.machine_guid or ""
    uuid = body.smbios_uuid or ""
    status_name = db.save_enrollment_request(
        proof_sha256,
        hostname,
        ip,
        serial,
        bad_id,
        guid or "",
        uuid or "",
    )
    if status_name is None:
        return {"status": "busy"}
    if status_name != "approved":
        return {"status": "pending"}
    row = db.get_enrollment_request_by_proof(proof_sha256)
    if not row or not row.get("api_key_enc"):
        return {"status": "approved"}
    if enroll_cleartext_blocked(request, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ENROLL_CLEARTEXT_MSG,
        )
    taken = db.take_enrollment_secrets(proof_sha256)
    if not taken or not taken.get("api_key_enc"):
        return {"status": "approved"}
    data_key = getattr(request.app.state, "data_key", "") or ""
    api_key = decrypt_secret(data_key, taken["api_key_enc"])
    signing_key = decrypt_secret(data_key, taken["signing_key_enc"] or "")
    if not api_key or not signing_key:
        return {"status": "approved"}
    body = {
        "status": "approved",
        "bad_id": taken["bad_id"],
        "api_key": api_key,
        "signing_key": signing_key,
    }
    mirrored = db.get_agent_update()
    archive_password = decrypt_secret(data_key, taken.get("archive_password_enc") or "")
    if (
        mirrored
        and archive_password
        and mirrored.get("sha256")
        and mirrored.get("version")
    ):
        body["archive_password"] = archive_password
        body["archive_sha256"] = mirrored["sha256"]
        body["archive_version"] = mirrored["version"]
    return body


@router.post("/enroll", response_model=EnrollResponse)
def enroll(
    body: EnrollRequest,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EnrollResponse:
    if enroll_cleartext_blocked(request, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ENROLL_CLEARTEXT_MSG,
        )
    _enforce_enroll_rate(request)
    bearer = extract_bearer(request.headers.get("authorization"))
    if not bearer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing enrollment code",
        )
    # Не сжигаем код здесь: upsert сожжёт его в той же транзакции, что и INSERT.
    grant_hash = enrollment_code_hash(bearer)
    if not db.enrollment_grant_usable(grant_hash, body.bad_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or spent enrollment code",
        )

    # SEC-001: enrollment token alone cannot un-revoke (early + DB TOCTOU guard).
    _REVOKED_DETAIL = (
        "Device access revoked; admin must rotate API key in web UI "
        "(enrollment token alone cannot un-revoke)"
    )

    existing = db.get_device_auth_row(body.bad_id)
    allow_existing = False
    if existing:
        if existing.get("revoked"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_REVOKED_DETAIL,
            )
        proof = (body.current_api_key or "").strip()
        if proof and verify_secret(existing["api_key_hash"], proof):
            allow_existing = True
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Device already enrolled; re-enroll requires current_api_key "
                    "or admin rotate-key"
                ),
            )

    api_key = generate_token("bad_ak_")
    api_key_hash = hash_secret(api_key)
    data_key = getattr(request.app.state, "data_key", "") or ""
    lookup = api_key_lookup(data_key, api_key) if data_key else None
    signing_private: Optional[str] = None
    signing_public: Optional[str] = None
    signing_fingerprint: Optional[str] = None
    if not existing:
        signing_private, signing_public, signing_fingerprint = new_device_signing_key()
    try:
        created = db.upsert_device_on_enroll(
            bad_id=body.bad_id,
            hostname=body.hostname,
            api_key_hash=api_key_hash,
            agent_version=body.agent_version,
            api_key_lookup=lookup,
            allow_existing=allow_existing,
            grant_code_hash=grant_hash,
            signing_pubkey=signing_public,
            signing_key_fingerprint=signing_fingerprint,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "grant_invalid":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or spent enrollment code",
            ) from exc
        if code == "device_revoked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_REVOKED_DETAIL,
            ) from exc
        if code == "bad_id_collision":
            logger.error("enroll bad_id collision for bad_id=%s", body.bad_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="bad_id collision for this bad_id",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already enrolled",
        ) from exc
    if created:
        try:
            smtp_row = db.get_smtp_settings()
            notify_enroll(
                db,
                smtp_row,
                bad_id=body.bad_id,
                hostname=body.hostname,
            )
        except Exception:  # noqa: BLE001
            logger.exception("SMTP enroll alert failed (ignored)")
    return EnrollResponse(
        api_key=api_key,
        bad_id=body.bad_id,
        signing_key=signing_private if created else None,
    )


@router.post("/heartbeat")
def heartbeat(
    body: HeartbeatRequest,
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if body.bad_id != device["bad_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="bad_id mismatch")
    target_id = body.bad_id
    # Omit/null config_local → keep previous; present (incl. keys:[]) → sanitize + store/clear.
    config_local_provided = body.config_local is not None
    config_local_payload = (
        body.config_local.sanitized() if body.config_local is not None else None
    )
    db.update_heartbeat(
        bad_id=target_id,
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
    if (body.agent_version or "").strip():
        db.mark_enrollment_installed(target_id)
    meta = db.get_device_meta(target_id) or {}
    meta = expire_uninstall_request_if_needed(db, target_id, meta)
    refresh_pending = refresh_request_pending(meta)
    send_uninstall = heartbeat_should_send_uninstall(meta)
    effective = db.compute_device_effective_config(
        target_id, use_inventory=refresh_pending or not body.config_version
    )
    assert effective is not None
    if body.config_version and body.config_version != effective["version"]:
        effective = db.compute_device_effective_config(
            target_id, use_inventory=True
        )
    resp: dict[str, Any] = {
        "status": "ok",
        "config_version": effective["version"],
    }
    config_matches = bool(
        body.config_version and body.config_version == effective["version"]
    )
    actions: dict[str, Any] = {}
    if refresh_pending:
        actions.update(heartbeat_actions_for_refresh(meta))
    if send_uninstall:
        actions["uninstall"] = True
    if not config_matches:
        resp["config"] = {
            "version": effective["version"],
            "settings": effective["settings"],
        }
    if actions:
        resp["actions"] = actions

    ack_patch = heartbeat_refresh_meta_patch(
        meta,
        last_inventory_at=body.last_inventory_at,
        config_version=body.config_version,
        effective_version=effective["version"],
    )
    if send_uninstall:
        ack_patch = {**(ack_patch or {}), **mark_uninstall_sent_patch()}
    if ack_patch:
        db.patch_device_meta(target_id, ack_patch)
    return resp


@router.post("/agent/signing-key")
def issue_agent_signing_key(
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, Optional[str]]:
    """Первая пара, пока открытый ключ пуст. Повтор этот путь не выпускает."""
    pubkey_now = str(device.get("signing_pubkey") or "").strip()
    if pubkey_now:
        return {"signing_key": None}
    old_fp = str(device.get("signing_key_fingerprint") or "").strip()
    private, public, fingerprint = new_device_signing_key()
    issued = db.claim_device_signing_key(device["bad_id"], public, fingerprint)
    logger.info(
        "signing key replace bad_id=%s old_fp=%s new_fp=%s issued=%s",
        device["bad_id"],
        old_fp,
        fingerprint if issued else "",
        "true" if issued else "false",
    )
    if not issued:
        return {"signing_key": None}
    return {"signing_key": private}


@router.get("/agent/config")
def agent_config(
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Enrolled-агент забирает свои эффективные remote settings (в рамках API key)."""
    effective = db.compute_device_effective_config(device["bad_id"])
    assert effective is not None
    return {
        "bad_id": device["bad_id"],
        "version": effective["version"],
        "settings": effective["settings"],
    }


def _log_inventory_signature(
    device: dict[str, Any],
    signed: dict[str, Any],
    signature: Optional[str],
    pubkey: str,
    status_code: int,
    detail: str,
) -> None:
    """Отказ — warning, приём — info. Секрет, канон и сама подпись в журнал не входят."""
    present = bool(signature)
    if present:
        raw = inventory_signing_bytes(signed)
        canon_len = str(len(raw))
        canon_sha = hashlib.sha256(raw).hexdigest()
        try:
            sig_len = str(len(base64.b64decode(signature or "", validate=True)))
        except (ValueError, TypeError):
            sig_len = "0"
    else:
        canon_len = ""
        canon_sha = ""
        sig_len = "0"
    key_fp = str(device.get("signing_key_fingerprint") or "").strip() if pubkey else ""
    line = (
        "inventory signature bad_id=%s status=%s detail=%s key_fp=%s "
        "signature_present=%s canon_len=%s canon_sha256=%s sig_len=%s"
    )
    fields = (
        device.get("bad_id") or "",
        status_code,
        detail,
        key_fp,
        "true" if present else "false",
        canon_len,
        canon_sha,
        sig_len,
    )
    if status_code == 401:
        logger.warning(line, *fields)
    else:
        logger.info(line, *fields)


def _accepted_inventory(
    body: InventoryRequest,
    device: dict[str, Any],
    db: Database,
    settings: Settings,
) -> dict[str, Any]:
    """Проверка bad_id, схемы, подписи и бюджета. Один путь для снимка и HTML-отчёта."""
    if body.bad_id != device["bad_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="bad_id mismatch")
    if body.schema_version not in settings.known_schema_versions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported schema_version: {body.schema_version}",
        )

    # Агент подписывает отправленный JSON без signature, не полный dump с null.
    signed = body.model_dump(exclude_unset=True)
    signature = signed.pop("signature", None)
    if isinstance(signature, str):
        signature = signature.strip() or None
    pubkey = (device.get("signing_pubkey") or "").strip()
    if pubkey:
        if signature and verify_inventory_signature(pubkey, signed, signature):
            pass
        else:
            detail = (
                "Invalid inventory signature"
                if signature
                else "Inventory signature required"
            )
            _log_inventory_signature(device, signed, signature, pubkey, 401, detail)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail,
            )
    elif signature:
        _log_inventory_signature(
            device, signed, signature, pubkey, 401, "Invalid inventory signature"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inventory signature",
        )
    elif db.get_bool_setting(
        "require_inventory_signature", settings.require_inventory_signature
    ):
        _log_inventory_signature(
            device, signed, signature, pubkey, 401, "Inventory signature required"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inventory signature required",
        )
    _log_inventory_signature(device, signed, signature, pubkey, 200, "")

    # Additive schema_version=2; strip dump bodies if agent ever sends them.
    payload = sanitize_inventory_payload(body.model_dump())
    # schema 1/2: неизвестные верхние ключи оставляем (текущие снимки). 3 — режем.
    if body.schema_version >= 3:
        payload = {key: value for key, value in payload.items() if key in INVENTORY_TOP_KEYS}
    payload.pop("signature", None)
    budget = inventory_budget_error(payload)
    if budget is not None:
        code, detail = budget
        raise HTTPException(status_code=code, detail=detail)
    return payload


def _snapshot_smbios_uuid(payload: Optional[dict[str, Any]]) -> Optional[str]:
    hardware = (
        payload.get("hardware")
        if isinstance(payload, dict) and isinstance(payload.get("hardware"), dict)
        else None
    )
    raw = hardware.get("smbios_uuid") if hardware else None
    return Database.normalize_smbios_uuid(raw)


@router.post("/inventory")
def inventory(
    body: InventoryRequest,
    request: Request,
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    payload = _accepted_inventory(body, device, db, settings)
    hostname = None
    host = payload.get("host") if isinstance(payload.get("host"), dict) else None
    if host:
        hostname = host.get("hostname")
    hardware = (
        payload.get("hardware")
        if isinstance(payload.get("hardware"), dict)
        else None
    )
    users = payload.get("users") if isinstance(payload.get("users"), dict) else None
    network = (
        payload.get("network") if isinstance(payload.get("network"), dict) else None
    )
    cached = inventory_meta_cache(
        host=host if isinstance(host, dict) else None,
        hardware=hardware,
        users=users,
        network=network,
    )
    identity = db.extract_identity_signals(hardware=hardware or {})
    meta = {
        "last_inventory_at": body.collected_at,
        **cached,
    }
    # Кэш сигналов дубля (не PK): serial/uuid/bios/board/disk — без auto-merge
    meta.update(db.identity_signals_for_meta(identity))
    new_uuid = _snapshot_smbios_uuid(payload)
    previous = db.latest_snapshot_payload(str(device["bad_id"]))
    old_uuid = _snapshot_smbios_uuid(previous)
    if new_uuid and old_uuid and new_uuid != old_uuid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="board changed")
    target_id = str(device["bad_id"])
    stored = db.store_inventory(
        bad_id=target_id,
        schema_version=body.schema_version,
        payload=payload,
        hostname=hostname,
        agent_version=body.agent_version,
        meta=meta,
        retention=settings.snapshot_retention,
    )
    if (body.agent_version or "").strip():
        db.mark_enrollment_installed(target_id)
    return {"status": "ok", "snapshot_id": stored["snapshot_id"]}


@router.post("/agent/report.html", response_class=HTMLResponse)
def agent_report_html(
    body: InventoryRequest,
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    """HTML карточки для уже зачисленного агента. Снимок не пишется в БД."""
    payload = _accepted_inventory(body, device, db, settings)
    from .web import render_device_report

    try:
        return render_device_report(db, settings, device["bad_id"], payload)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")


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


def _device_card(db: Database, ref: str) -> dict[str, Any] | None:
    detail = db.get_device_detail(ref)
    if not detail:
        return None
    detail["duplicates"] = db.find_duplicate_devices(ref)
    return detail


def _note_integration_read(db: Database, reader: dict[str, str]) -> None:
    if reader.get("kind") == "integration":
        from .integrations import record_use

        record_use(db, reader["id"])


@router.get("/devices/{bad_id}")
def get_device(
    bad_id: str,
    db: Database = Depends(get_db),
    reader: dict[str, str] = Depends(_device_reader),
) -> dict[str, Any]:
    detail = _device_card(db, bad_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    _note_integration_read(db, reader)
    return detail


def _integration_http_error(exc: Exception) -> HTTPException:
    from .integrations import IntegrationError

    if not isinstance(exc, IntegrationError):
        raise exc
    if exc.code == "name":
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid name")
    if exc.code == "too_many":
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many open integration requests",
        )
    if exc.code == "not_found":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if exc.code in {"no_data_key", "token_missing"}:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Integration token is not available",
        )
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Integration state conflict")


@router.post("/integrations/requests")
def create_integration_request(
    body: IntegrationRequestBody,
    request: Request,
    db: Database = Depends(get_db),
) -> dict[str, str]:
    from .integrations import IntegrationError, create_request

    limiter = getattr(request.app.state, "integration_limiter", None)
    if limiter is not None and not limiter.allow(client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Integration request rate limit exceeded",
        )
    data_key = getattr(request.app.state, "data_key", "") or ""
    try:
        return create_request(db, data_key, body.name)
    except IntegrationError as exc:
        raise _integration_http_error(exc) from exc


@router.get("/integrations/requests/{integration_id}")
def poll_integration_request(
    integration_id: str,
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    db: Database = Depends(get_db),
) -> dict[str, str]:
    from .integrations import IntegrationError, poll_request

    secret = extract_bearer(authorization) or ""
    if not secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing request secret")
    data_key = getattr(request.app.state, "data_key", "") or ""
    try:
        return poll_request(db, data_key, integration_id, secret)
    except IntegrationError as exc:
        raise _integration_http_error(exc) from exc


@router.post("/integrations/lookup")
def lookup_integration_device(
    body: IntegrationLookupBody,
    db: Database = Depends(get_db),
    reader: dict[str, str] = Depends(_device_reader),
) -> dict[str, Any]:
    detail = _device_card(db, body.bad_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    _note_integration_read(db, reader)
    return detail


@router.post("/devices/{bad_id}/revoke")
def revoke_device(
    bad_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.set_device_revoked(bad_id, True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "bad_id": bad_id, "revoked": True}


@router.post("/devices/{bad_id}/request-refresh")
def request_device_refresh_api(
    bad_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not set_device_refresh_request(db, bad_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "bad_id": bad_id, "refresh_requested": True}


@router.post("/devices/{bad_id}/rotate-key")
def rotate_device_key(
    bad_id: str,
    request: Request,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.get_device_detail(bad_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    api_key = generate_token("bad_ak_")
    data_key = getattr(request.app.state, "data_key", "") or ""
    lookup = api_key_lookup(data_key, api_key) if data_key else None
    db.rotate_device_api_key(
        bad_id, hash_secret(api_key), api_key_lookup=lookup
    )
    return {
        "status": "ok",
        "bad_id": bad_id,
        "api_key": api_key,
        "revoked": False,
    }


@router.post("/devices/{bad_id}/archive")
def archive_device(
    bad_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.set_device_archived(bad_id, True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "bad_id": bad_id, "archived": True}


@router.post("/devices/{bad_id}/restore")
def restore_device(
    bad_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.set_device_archived(bad_id, False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "bad_id": bad_id, "archived": False}


@router.delete("/devices/{bad_id}")
def delete_device(
    bad_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    if not db.delete_device(bad_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"status": "ok", "bad_id": bad_id, "deleted": True}


@router.get("/events")
def list_events(
    bad_id: str | None = Query(default=None, max_length=128),
    q: str | None = Query(default=None, max_length=128),
    importance: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    device_filter = (bad_id or "").strip() or None
    q_filter = (q or "").strip() or None
    imp = (importance or "").strip().casefold() or None
    return {
        "events": db.list_device_events(
            bad_id=device_filter,
            limit=limit,
            offset=offset,
            q=q_filter,
            importance=imp,
            include_detail=False,
        ),
        "total": db.count_device_events(
            bad_id=device_filter, q=q_filter, importance=imp
        ),
        "limit": limit,
        "offset": offset,
    }


@router.put("/devices/{bad_id}/tags")
def put_device_tags(
    bad_id: str,
    body: DeviceTagsBody,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        saved = db.set_device_tags(bad_id, body.tags)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        ) from exc
    return {"bad_id": bad_id, "tags": saved}


@router.get("/agent/update/check")
def agent_update_check(
    request: Request,
    current: str = Query(default="", max_length=64),
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Агенты спрашивают целевой архив (effective update_target)."""
    return check_update(
        db,
        current=current or "0.0.0",
        device=dict(device) if device is not None else None,
        data_key=getattr(request.app.state, "data_key", "") or "",
    )


class LinkProgressBody(BaseModel):
    received: int
    total: int
    state: str
    error: Optional[str] = None


def _range_start(header: str) -> Optional[int]:
    text = (header or "").strip()
    if not text.lower().startswith("bytes="):
        return None
    left = text[6:].split("-", 1)[0].strip()
    if not left.isdigit():
        return None
    return int(left)


@router.get("/agent/update/archive")
def agent_update_archive(
    request: Request,
    version: str = Query(default="", max_length=64),
    _device=Depends(require_api_key),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
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
            detail="Mirrored archive name is unsafe",
        ) from exc
    if not safe_name.lower().endswith(".arc"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    path = Path(mirrored["file_path"]).resolve()
    updates_root = settings.agent_updates_dir.resolve()
    try:
        path.relative_to(updates_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mirrored archive path escapes updates dir",
        ) from exc
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mirrored archive file missing on disk",
        )
    total = path.stat().st_size
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'attachment; filename="{safe_name}"',
    }
    start = _range_start(request.headers.get("range") or "")
    if start is not None and start < total:
        with path.open("rb") as handle:
            handle.seek(start)
            chunk = handle.read()
        headers["Content-Range"] = f"bytes {start}-{total - 1}/{total}"
        return Response(
            content=chunk,
            status_code=206,
            media_type="application/octet-stream",
            headers=headers,
        )
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=safe_name,
        headers={"Accept-Ranges": "bytes"},
    )


@router.post("/agent/link-progress")
def agent_link_progress(
    body: LinkProgressBody,
    device=Depends(require_api_key),
    db: Database = Depends(get_db),
) -> dict[str, str]:
    db.set_link_progress(
        str(device["bad_id"]),
        body.received,
        body.total,
        body.state,
        body.error or "",
    )
    return {"status": "ok"}


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
    request: Request,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    try:
        record = sync_from_github(
            db,
            settings,
            data_key=getattr(request.app.state, "data_key", "") or "",
        )
    except Exception as exc:  # noqa: BLE001 — показать ошибки sync админу
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub sync failed: {exc}",
        ) from exc
    return {"status": "ok", "mirrored": record, "latest": db.get_agent_update()}


@router.post("/admin/agent-update/upload")
async def admin_agent_update_upload(
    request: Request,
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
            data_key=getattr(request.app.state, "data_key", "") or "",
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
    wait: bool = Query(default=False),
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
    wait: bool = Query(default=False),
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
    wait: bool = Form(False),
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


@router.get("/admin/security-status")
def admin_security_status(
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Theme A: HTTPS-first + SEC-005 (no plaintext secrets)."""
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


@router.get("/admin/devices/{bad_id}/config")
def admin_device_config(
    bad_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    effective = db.compute_device_effective_config(bad_id)
    if not effective:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {
        "bad_id": bad_id,
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


@router.put("/admin/devices/{bad_id}/config-override")
def admin_set_device_override(
    bad_id: str,
    body: DeviceConfigOverrideBody,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    cleaned = sanitize_settings(body.settings)
    try:
        override = db.set_device_config_override(bad_id, cleaned)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        ) from exc
    effective = db.compute_device_effective_config(bad_id)
    assert effective is not None
    return {
        "override": override,
        "effective": effective["settings"],
        "version": effective["version"],
    }


@router.delete("/admin/devices/{bad_id}/config-override")
def admin_delete_device_override(
    bad_id: str,
    _admin: str = Depends(require_admin_token),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    detail = db.get_device_detail(bad_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    db.delete_device_config_override(bad_id)
    effective = db.compute_device_effective_config(bad_id)
    assert effective is not None
    return {
        "status": "ok",
        "effective": effective["settings"],
        "version": effective["version"],
    }

