"""Device silence / health helpers for the web UI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional


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
) -> dict[str, Any]:
    """Return {status: ok|stale|unknown, age_seconds, stale_after_seconds}."""
    threshold = max(1, int(stale_after_seconds))
    seen = parse_utc(last_seen_at)
    if seen is None:
        return {
            "status": "unknown",
            "age_seconds": None,
            "stale_after_seconds": threshold,
            "label": "unknown",
        }
    clock = now or datetime.now(timezone.utc)
    age = max(0, int((clock - seen).total_seconds()))
    stale = age > threshold
    return {
        "status": "stale" if stale else "ok",
        "age_seconds": age,
        "stale_after_seconds": threshold,
        "label": "stale" if stale else "OK",
    }


def health_snippet(meta: Optional[dict[str, Any]]) -> Optional[str]:
    """Best-effort short health text from device meta (if agent/sibling adds it)."""
    if not meta or not isinstance(meta, dict):
        return None
    for key in ("health", "last_health", "health_status"):
        value = meta.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text[:240]
        if isinstance(value, (dict, list)):
            try:
                return json.dumps(value, ensure_ascii=False, separators=(",", ":"))[:240]
            except (TypeError, ValueError):
                continue
        text = str(value).strip()
        if text:
            return text[:240]
    return None


def normalize_tags(raw: Any) -> list[str]:
    """Normalize tags from JSON list, comma-separated string, or iterable."""
    items: list[str] = []
    if raw is None:
        return []
    if isinstance(raw, str):
        # Allow comma/space separated form input.
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
        # Keep original casing of first occurrence; match case-insensitively.
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
