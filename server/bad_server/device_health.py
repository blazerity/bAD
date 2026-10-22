"""Хелперы тишины / health устройств для web UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings
    from .db import Database

DEVICE_STALE_SITE_SECRET_KEY = "device_stale_after_seconds"
DEVICE_STALE_MIN_SECONDS = 60
DEVICE_STALE_MAX_SECONDS = 604800  # 7 суток


def _parse_site_stale_seconds(raw: Optional[str]) -> Optional[int]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = int(text)
    except (TypeError, ValueError):
        return None
    if DEVICE_STALE_MIN_SECONDS <= value <= DEVICE_STALE_MAX_SECONDS:
        return value
    return None


def effective_stale_after_seconds(db: Database, settings: Settings) -> int:
    """Порог «устарел»: site_secret в БД или env BAD_DEVICE_STALE_AFTER_SECONDS."""
    override = _parse_site_stale_seconds(
        db.get_site_secret(DEVICE_STALE_SITE_SECRET_KEY)
    )
    if override is not None:
        return override
    return int(settings.device_stale_after_seconds)


def parse_utc(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    text = str(ts).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def device_silence_status(
    last_seen_at: Optional[str],
    *,
    stale_after_seconds: int,
    now: Optional[datetime] = None,
) -> dict[str, str]:
    """Вернуть {status: ok|stale|unknown} для CSS-бейджа / отображения."""
    threshold = max(1, int(stale_after_seconds))
    seen = parse_utc(last_seen_at)
    if seen is None:
        return {"status": "unknown"}
    clock = now or datetime.now(timezone.utc)
    age = max(0, int((clock - seen).total_seconds()))
    return {"status": "stale" if age > threshold else "ok"}


def health_snippet(meta: Optional[dict[str, Any]]) -> Optional[str]:
    """Короткий текст health из полей heartbeat в device meta."""
    if not meta or not isinstance(meta, dict):
        return None
    parts: list[str] = []
    if "last_inventory_ok" in meta:
        ok = meta.get("last_inventory_ok")
        if ok is True:
            parts.append("inventory ok")
        elif ok is False:
            err = str(meta.get("last_inventory_error") or "").strip()
            parts.append(f"inventory fail: {err}" if err else "inventory fail")
    uptime = meta.get("agent_uptime_seconds")
    if isinstance(uptime, int) and uptime >= 0:
        parts.append(f"uptime {uptime}s")
    free = meta.get("system_drive_free_bytes")
    if isinstance(free, int) and free >= 0:
        parts.append(f"free {free} B")
    if not parts:
        return None
    return "; ".join(parts)[:240]


def normalize_tags(raw: Any) -> list[str]:
    """Нормализовать теги из JSON-списка, строки через запятую/точку с запятой/перевод строки или iterable."""
    items: list[str] = []
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = raw.replace(";", ",").replace("\n", ",").split(",")
        items = [p.strip() for p in parts]
    elif isinstance(raw, (list, tuple, set)):
        for item in raw:
            if item is None:
                continue
            items.append(str(item).strip())
    else:
        items = [str(raw).strip()]

    seen: set[str] = set()
    out: list[str] = []
    for tag in items:
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        if len(tag) > 64:
            tag = tag[:64]
        seen.add(key)
        out.append(tag)
        if len(out) >= 32:
            break
    return out
