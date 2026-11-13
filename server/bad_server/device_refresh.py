"""Панель: одноразовый запрос refresh политики / inventory / update check через heartbeat meta."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .db import Database, utc_now
from .device_health import parse_utc

REFRESH_META_KEYS = (
    "refresh_requested_at",
    "refresh_inventory",
    "refresh_update_check",
)

REFRESH_TTL = timedelta(hours=24)


def refresh_request_pending(meta: dict[str, Any], *, now: Optional[datetime] = None) -> bool:
    raw = meta.get("refresh_requested_at")
    if not raw or not isinstance(raw, str):
        return False
    requested_at = parse_utc(raw)
    if not requested_at:
        return False
    now = now or datetime.now(timezone.utc)
    return now - requested_at <= REFRESH_TTL


def heartbeat_actions_for_refresh(meta: dict[str, Any]) -> dict[str, bool]:
    actions: dict[str, bool] = {}
    if meta.get("refresh_inventory", True):
        actions["inventory"] = True
    if meta.get("refresh_update_check", True):
        actions["update_check"] = True
    return actions


def clear_refresh_meta_patch() -> dict[str, None]:
    return {key: None for key in REFRESH_META_KEYS}


def _utc_iso_ge(later: Optional[str], earlier: Optional[str]) -> bool:
    """True if both parse and later >= earlier (implicit heartbeat ack)."""
    if not later or not earlier:
        return False
    a = parse_utc(str(later))
    b = parse_utc(str(earlier))
    if a is None or b is None:
        return False
    return a >= b


def heartbeat_refresh_meta_patch(
    meta: dict[str, Any],
    *,
    last_inventory_at: Optional[str],
    config_version: Optional[str],
    effective_version: str,
) -> Optional[dict[str, Any]]:
    """Clear refresh meta only from existing heartbeat fields (no new protocol).

    ``last_inventory_at`` acks ``refresh_inventory``; ``config_version`` acks
    policy config. ``refresh_update_check`` has no ack field — meta expires at TTL.
    """
    if not meta.get("refresh_requested_at"):
        return None
    if not refresh_request_pending(meta):
        return clear_refresh_meta_patch()

    requested_at = meta.get("refresh_requested_at")
    if not isinstance(requested_at, str):
        return None

    want_inv = meta.get("refresh_inventory", True) is not False
    want_upd = meta.get("refresh_update_check", True) is not False
    inv_ok = not want_inv or _utc_iso_ge(last_inventory_at, requested_at)
    cfg_ok = bool(
        config_version
        and effective_version
        and config_version == effective_version
    )

    patch: dict[str, Any] = {}
    if want_inv and inv_ok:
        patch["refresh_inventory"] = None

    if inv_ok and cfg_ok and not want_upd:
        for key, value in clear_refresh_meta_patch().items():
            patch[key] = value
        return patch

    return patch or None


def set_device_refresh_request(
    db: Database,
    bad_id: str,
    *,
    refresh_inventory: bool = True,
    refresh_update_check: bool = True,
) -> bool:
    if not db.get_device_detail(bad_id):
        return False
    db.patch_device_meta(
        bad_id,
        {
            "refresh_requested_at": utc_now(),
            "refresh_inventory": refresh_inventory,
            "refresh_update_check": refresh_update_check,
        },
    )
    return True
