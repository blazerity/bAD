"""Хелперы тишины / health устройств для web UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings
    from .db import Database

DEVICE_STALE_SITE_SECRET_KEY = "device_stale_after_seconds"
DEVICE_RECENT_SITE_SECRET_KEY = "device_recent_after_seconds"
DEVICE_STALE_MIN_SECONDS = 60
DEVICE_STALE_MAX_SECONDS = 604800  # 7 суток
DEVICE_RECENT_DEFAULT_SECONDS = 600  # 10 минут, пока секрета нет


def parse_site_stale_seconds(raw: Optional[str]) -> Optional[int]:
    """Распарсить секунды порога stale; вне диапазона → None."""
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
    override = parse_site_stale_seconds(
        db.get_site_secret(DEVICE_STALE_SITE_SECRET_KEY)
    )
    if override is not None:
        return override
    return int(settings.device_stale_after_seconds)


def parse_site_recent_seconds(raw: Optional[str]) -> Optional[int]:
    """Секунды порога «Недавно». Пустое и нечисло — нет секрета."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = int(text)
    except (TypeError, ValueError):
        return None
    if value < 60:
        return None
    return value


def effective_recent_after_seconds(db: Database) -> int:
    """Порог «Недавно» в секундах. Без секрета — 10 минут. Секрет не пишет."""
    stored = parse_site_recent_seconds(
        db.get_site_secret(DEVICE_RECENT_SITE_SECRET_KEY)
    )
    if stored is None:
        return DEVICE_RECENT_DEFAULT_SECONDS
    return stored


def badge_recent_after_seconds(recent_after_seconds: int, stale_after_seconds: int) -> int:
    """Если «Недавно» не короче «устарел», бейдж «Недавно» не показывается."""
    recent = int(recent_after_seconds)
    stale = int(stale_after_seconds)
    if recent >= stale:
        return stale
    return recent


def stale_days_form(seconds: int) -> tuple[int, Optional[int]]:
    """Поле дней и, если секунды не кратны суткам, действующие минуты."""
    seconds = int(seconds)
    if seconds > 0 and seconds % 86400 == 0:
        days = seconds // 86400
        if 1 <= days <= 7:
            return days, None
    minutes = max(1, seconds // 60)
    return 1, minutes


def retention_threshold_seconds(
    stale_days: int, recent_minutes: int
) -> tuple[int, int] | str:
    """Секунды для записи или текст ошибки. При ошибке ничего не писать."""
    if stale_days < 1 or stale_days > 7:
        return "Порог «устарел»: от 1 до 7 дней"
    if recent_minutes < 1:
        return "Порог «Недавно»: целое число минут от 1"
    stale_sec = stale_days * 86400
    recent_sec = recent_minutes * 60
    if recent_sec >= stale_sec:
        return "Порог «Недавно» должен быть короче порога «устарел»"
    return stale_sec, recent_sec


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


def parse_iso(raw: object) -> Optional[datetime]:
    """ISO-8601 as written: Z → +00:00, naive stays naive."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


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
