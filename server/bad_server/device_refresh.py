"""Панель: одноразовый запрос refresh политики / inventory / update check через heartbeat meta."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .db import Database, utc_now

REFRESH_META_KEYS = (
    "refresh_requested_at",
    "refresh_inventory",
    "refresh_update_check",
)

REFRESH_TTL = timedelta(hours=24)


def _parse_utc_iso(raw: str) -> Optional[datetime]:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def refresh_request_pending(meta: dict[str, Any], *, now: Optional[datetime] = None) -> bool:
    raw = meta.get("refresh_requested_at")
    if not raw or not isinstance(raw, str):
        return False
    requested_at = _parse_utc_iso(raw)
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


def set_device_refresh_request(
    db: Database,
    device_id: str,
    *,
    refresh_inventory: bool = True,
    refresh_update_check: bool = True,
) -> bool:
    if not db.get_device_detail(device_id):
        return False
    db.patch_device_meta(
        device_id,
        {
            "refresh_requested_at": utc_now(),
            "refresh_inventory": refresh_inventory,
            "refresh_update_check": refresh_update_check,
        },
    )
    return True
