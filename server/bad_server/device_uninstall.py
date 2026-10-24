"""Удалённое снятие агента с ПК через heartbeat actions.uninstall (meta JSON)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from .db import Database, utc_now

UNINSTALL_META_KEYS = (
    "uninstall_requested_at",
    "uninstall_sent_at",
    "uninstall_not_delivered_at",
)

UNINSTALL_TTL = timedelta(days=7)

UninstallBadge = Literal["removing", "sent", "failed"]


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


def _now(now: Optional[datetime] = None) -> datetime:
    return now or datetime.now(timezone.utc)


def uninstall_request_active(
    meta: dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> bool:
    """Команда ещё не ушла в heartbeat и TTL не истёк."""
    requested = meta.get("uninstall_requested_at")
    if not requested or not isinstance(requested, str):
        return False
    if meta.get("uninstall_sent_at"):
        return False
    requested_at = _parse_utc_iso(requested)
    if not requested_at:
        return False
    return _now(now) - requested_at <= UNINSTALL_TTL


def expire_uninstall_request_if_needed(
    db: Database,
    device_id: str,
    meta: dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Снять просроченный uninstall_requested_at (статус «Не дошло»)."""
    if not uninstall_request_active(meta, now=now):
        requested = meta.get("uninstall_requested_at")
        sent = meta.get("uninstall_sent_at")
        if requested and not sent:
            requested_at = _parse_utc_iso(str(requested))
            if requested_at and _now(now) - requested_at > UNINSTALL_TTL:
                db.patch_device_meta(
                    device_id,
                    {
                        "uninstall_requested_at": None,
                        "uninstall_not_delivered_at": utc_now(),
                    },
                )
                out = dict(meta)
                out["uninstall_requested_at"] = None
                out["uninstall_not_delivered_at"] = utc_now()
                return out
    return meta


def heartbeat_should_send_uninstall(meta: dict[str, Any], *, now: Optional[datetime] = None) -> bool:
    return uninstall_request_active(meta, now=now)


def mark_uninstall_sent_patch() -> dict[str, str]:
    sent = utc_now()
    return {
        "uninstall_sent_at": sent,
        "uninstall_requested_at": None,
        "uninstall_not_delivered_at": None,
    }


def clear_uninstall_request_patch() -> dict[str, None]:
    return {"uninstall_requested_at": None}


def start_new_uninstall_request_patch() -> dict[str, str]:
    return {
        "uninstall_requested_at": utc_now(),
        "uninstall_sent_at": None,
        "uninstall_not_delivered_at": None,
    }


def uninstall_badge(meta: dict[str, Any], *, now: Optional[datetime] = None) -> Optional[UninstallBadge]:
    sent = meta.get("uninstall_sent_at")
    if sent and str(sent).strip():
        return "sent"
    if meta.get("uninstall_not_delivered_at") and str(
        meta.get("uninstall_not_delivered_at") or ""
    ).strip():
        return "failed"
    requested = meta.get("uninstall_requested_at")
    if not requested or not str(requested).strip():
        return None
    if uninstall_request_active(meta, now=now):
        return "removing"
    return "failed"


def uninstall_ui_context(meta: dict[str, Any], *, now: Optional[datetime] = None) -> dict[str, Any]:
    badge = uninstall_badge(meta, now=now)
    return {
        "badge": badge,
        "badge_label": {
            "removing": "Удаляется",
            "sent": "Команда отправлена",
            "failed": "Не дошло",
        }.get(badge or "", ""),
        "pending": badge == "removing",
        "can_order": badge not in ("removing",),
    }


def request_device_uninstall(db: Database, device_id: str) -> tuple[bool, str]:
    """Поставить команду снятия. False + reason если нельзя."""
    detail = db.get_device_detail(device_id)
    if not detail:
        return False, "missing"
    if detail.get("revoked"):
        return False, "revoked"
    meta = detail.get("meta") or {}
    if isinstance(meta, str):
        meta = {}
    if uninstall_request_active(meta):
        return True, "already_pending"
    db.patch_device_meta(device_id, start_new_uninstall_request_patch())
    return True, "ok"


def cancel_device_uninstall(db: Database, device_id: str) -> bool:
    detail = db.get_device_detail(device_id)
    if not detail:
        return False
    meta = detail.get("meta") or {}
    if not uninstall_request_active(meta):
        return False
    db.patch_device_meta(device_id, clear_uninstall_request_patch())
    return True


def device_uninstall_confirm_value(detail: dict[str, Any]) -> str:
    host = (detail.get("hostname") or "").strip()
    if host:
        return host
    return str(detail.get("device_id") or "").strip()
