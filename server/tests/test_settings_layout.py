"""Панель параметров: галки почты, вкладка «Основные», порог «Недавно»."""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bad_server.device_health import (
    DEVICE_RECENT_SITE_SECRET_KEY,
    DEVICE_STALE_SITE_SECRET_KEY,
    effective_recent_after_seconds,
)
from bad_server.event_importance import _EVENT_IMPORTANCE
from bad_server.web import (
    _EVENT_TYPE_LABELS_RU,
    _NOTIFY_CHECK_LABELS_RU,
    _commit_retention,
    _device_freshness_tier,
    _notify_check_groups,
    _retention_context,
    _save_inventory_signature,
    settings_home,
)

_ROOT = Path(__file__).resolve().parents[1]
_CSS = (_ROOT / "bad_server" / "static" / "style.css").read_text(encoding="utf-8")
_UPDATES = (
    _ROOT / "bad_server" / "templates" / "updates_settings.html"
).read_text(encoding="utf-8")


class _Settings:
    device_stale_after_seconds = 3600
    require_inventory_signature = False


class _Db:
    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self.secrets = dict(secrets or {})
        self.written: list[tuple[str, str]] = []

    def get_site_secret(self, key: str) -> str | None:
        return self.secrets.get(key)

    def set_site_secret(self, key: str, value: str) -> None:
        self.written.append((key, value))
        self.secrets[key] = value

    def get_retention_settings(self) -> dict[str, int]:
        return {"events_days": 90, "inventory_days": 180}

    def update_retention_settings(self, **kwargs: int) -> None:
        self.retention = kwargs

    def get_bool_setting(self, key: str, default: bool) -> bool:
        raw = self.secrets.get(key)
        if raw is None or not str(raw).strip():
            return default
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _media_block(css: str, width: str) -> str:
    needle = f"@media (max-width: {width})"
    start = css.find(needle)
    assert start >= 0
    brace = css.find("{", start)
    depth = 0
    for index in range(brace, len(css)):
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return css[brace : index + 1]
    raise AssertionError(needle)


def test_mail_checkbox_labels_and_groups() -> None:
    assert _NOTIFY_CHECK_LABELS_RU["ram_bytes_change"] == (
        "Сменился объём оперативной памяти"
    )
    assert _EVENT_TYPE_LABELS_RU["ram_bytes_change"] == "ОЗУ"
    assert "disk_change" not in _NOTIFY_CHECK_LABELS_RU
    for event_type in _EVENT_IMPORTANCE:
        assert event_type in _NOTIFY_CHECK_LABELS_RU
    titles = [title for title, _items in _notify_check_groups()]
    assert titles == ["Критичные", "Высокие", "Средние", "Низкие"]


def _without_media(css: str) -> str:
    parts: list[str] = []
    index = 0
    while True:
        start = css.find("@media", index)
        if start < 0:
            parts.append(css[index:])
            break
        parts.append(css[index:start])
        brace = css.find("{", start)
        depth = 0
        end = brace
        for end in range(brace, len(css)):
            if css[end] == "{":
                depth += 1
            elif css[end] == "}":
                depth -= 1
                if depth == 0:
                    break
        index = end + 1
    return "".join(parts)


def test_notify_grid_collapses_at_phone_width() -> None:
    base = _without_media(_CSS)
    rule = base.split(".notify-checks-grid {", 1)[1].split("}", 1)[0]
    assert "minmax(0, 1fr) minmax(0, 1fr)" in rule
    phone = _media_block(_CSS, "640px")
    assert ".notify-checks-grid" in phone
    wide = _media_block(_CSS, "1100px")
    assert ".notify-checks-grid" not in wide
    assert ".dash-ops-grid" in wide


def test_general_settings_and_signature_flag() -> None:
    assert settings_home(object()).headers["location"] == "/settings/general"
    assert "require_inventory_signature" not in _UPDATES
    db = _Db()
    _save_inventory_signature(db, "1")
    _save_inventory_signature(db, "")
    assert db.written == [
        ("require_inventory_signature", "1"),
        ("require_inventory_signature", "0"),
    ]


def test_recent_threshold_and_badge() -> None:
    assert effective_recent_after_seconds(_Db()) == 600
    assert effective_recent_after_seconds(
        _Db({DEVICE_RECENT_SITE_SECRET_KEY: "900"})
    ) == 900
    now = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def seen(seconds: int) -> str:
        return (now - timedelta(seconds=seconds)).isoformat()

    assert (
        _device_freshness_tier(
            seen(9 * 60),
            stale_after_seconds=3600,
            recent_after_seconds=600,
            now=now,
        )
        == "online"
    )
    assert (
        _device_freshness_tier(
            seen(11 * 60),
            stale_after_seconds=3600,
            recent_after_seconds=600,
            now=now,
        )
        == "recent"
    )
    assert (
        _device_freshness_tier(
            seen(3601),
            stale_after_seconds=3600,
            recent_after_seconds=600,
            now=now,
        )
        == "stale"
    )
    assert "// 3" not in inspect.getsource(_device_freshness_tier)


def test_stale_days_post_and_get() -> None:
    db = _Db({DEVICE_STALE_SITE_SECRET_KEY: "3600"})
    ctx = _retention_context(db, _Settings(), user=object())
    assert ctx["stale_after_days"] == 1
    assert ctx["stale_note_minutes"] == 60
    assert db.written == []
    assert db.secrets[DEVICE_STALE_SITE_SECRET_KEY] == "3600"

    saved = _Db()
    assert (
        _commit_retention(
            saved,
            events_days=90,
            inventory_days=180,
            stale_days=2,
            recent_minutes=10,
        )
        is None
    )
    assert (DEVICE_STALE_SITE_SECRET_KEY, "172800") in saved.written

    blocked = _Db({DEVICE_STALE_SITE_SECRET_KEY: "3600"})
    error = _commit_retention(
        blocked,
        events_days=90,
        inventory_days=180,
        stale_days=1,
        recent_minutes=1440,
    )
    assert error
    assert blocked.written == []
    assert blocked.secrets[DEVICE_STALE_SITE_SECRET_KEY] == "3600"
