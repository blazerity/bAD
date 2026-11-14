from __future__ import annotations

import csv
import html
import io
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

from markupsafe import Markup
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from . import __version__, panel_root
from .agent_config import (
    ALLOWED_SETTING_KEYS,
    CONDITION_FIELDS,
    CONDITION_OPS,
    DEFAULT_AGENT_SETTINGS,
    UPDATE_TARGET_LATEST,
    sanitize_conditions,
    sanitize_settings,
    sanitize_update_target,
)
from .auth import (
    authenticate_web_user,
    current_web_user,
    get_data_key,
    get_db,
    get_session_secret,
    load_ldap_view,
    require_web_admin,
    require_web_user,
)
from .config import Settings, get_settings
from .crypto_util import decrypt_secret, encrypt_secret
from .csrf import cookie_secure_for_request, ensure_csrf, get_csrf_token, set_csrf_cookie
from .device_refresh import set_device_refresh_request
from .db import Database
from .device_health import (
    DEVICE_RECENT_SITE_SECRET_KEY,
    DEVICE_STALE_SITE_SECRET_KEY,
    badge_recent_after_seconds,
    device_silence_status,
    effective_recent_after_seconds,
    effective_stale_after_seconds,
    health_snippet,
    parse_iso,
    parse_utc,
    retention_threshold_seconds,
    stale_days_form,
)
from .ldap_client import settings_from_row, test_connection
from .security import (
    api_key_lookup,
    generate_token,
    hash_secret,
    new_device_signing_key,
    verify_secret,
)
from .sessions import (
    FLASH_COOKIE,
    FLASH_MAX_AGE,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    WebUser,
    dump_flash,
    dump_session,
    load_flash,
)
from .agent_update import (
    delete_msi_version,
    ingest_uploaded_msi,
    ops_update_signals,
    set_latest_msi_version,
    sync_from_github,
)
from .backup import backup_keys_status, backup_status, run_daily_backup
from .http_bootstrap import HTTP_SENSITIVE_MSG, client_ip, sensitive_over_http_blocked
from .device_meta import (
    format_logged_on_display,
    inventory_meta_cache,
    meta_search_haystack,
    normalize_logged_on_list,
    normalize_logged_on_user,
)
from .server_runtime import build_server_runtime
from .panel_search import (
    device_match_label,
    device_match_parts,
    event_match_label,
    highlight_match,
    matched_serial_subtitle,
)
from .fleet_buckets import (
    disk_bucket_bytes,
    disk_role,
    format_cpu_short,
    format_ram_list_cell,
    meta_facet_matches,
    normalize_os_caption,
)
from .device_uninstall import (
    cancel_device_uninstall,
    device_uninstall_confirm_value,
    request_device_uninstall,
    uninstall_confirm_matches,
    uninstall_ui_context,
)
from .ops_panel import (
    aggregate_incident_feed,
    build_attention_queue,
    build_bootstrap_checklist,
    build_bootstrap_progress,
    build_config_winner,
    build_dashboard_stats,
    build_wave_counts,
    device_has_agent_local,
    enrich_overview_ops_signals,
    filter_devices_by_wave,
    normalize_wave_filter,
)
from .security_ops import merge_security_into_ops, security_status
from .site_bundle import build_key_escrow_archive, build_site_bundle
from .tls_ops import (
    https_panel_url,
    read_domain_from_env,
    save_tls_materials,
    tls_panel_mode,
    tls_status,
    wait_for_apply,
)
from .server_update import (
    check_updates as server_check_updates,
    list_remote_branches,
    poll_msi_workflow,
    read_current as server_read_current,
    releases_dir,
    request_apply as server_request_apply,
    request_set_github_token,
    set_preferred_branch,
    status_panel as server_status_panel,
    trigger_msi_workflow,
    outcome_for_apply_request as server_outcome_for_apply_request,
)
from .event_importance import (
    FILTER_PRESET_LABELS_RU,
    IMPORTANCE_LABELS_RU,
    _EVENT_IMPORTANCE,
    event_importance,
)
from .smtp_mail import (
    DEFAULT_NOTIFY,
    build_hardware_email,
    default_digest_weekdays,
    digest_schedule_preview_ru,
    dump_notify_flags,
    parse_digest_weekdays,
    parse_notify_flags,
    parse_recipients,
    send_email,
)
from .web_http import (
    _clear_session_cookie,
    _flash_check,
    _html,
    _see_other,
    _set_session_cookie,
    _take_flash,
    templates,
)




def _format_bytes(value: object, empty: str = "—") -> str:
    """Человекочитаемый размер (KiB/MiB/…) для Speccy-карточки."""
    if value is None:
        return empty
    try:
        n = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return empty
    if n < 0:
        return empty
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    if i == 0:
        return f"{n} {units[i]}"
    text = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{text} {units[i]}"



def _format_os(os_info: object, empty: str = "—") -> str:
    if not isinstance(os_info, dict):
        return empty
    parts = [os_info.get("caption"), os_info.get("version"), os_info.get("arch")]
    text = " / ".join(str(p) for p in parts if p)
    return text or empty



_CHASSIS_LABELS_RU = {
    "laptop": "Ноутбук",
    "desktop": "Десктоп",
    "server": "Сервер",
    "vm": "ВМ",
    "other": "Другое",
}



def _format_chassis(value: object, empty: str = "") -> str:
    if value is None:
        return empty
    key = str(value).strip().lower()
    if not key:
        return empty
    return _CHASSIS_LABELS_RU.get(key, str(value))



def _normalize_chassis_type(value: object) -> str:
    from .device_meta import normalize_chassis_type

    return normalize_chassis_type(value) or "other"



def _chassis_type_from_device(device: dict) -> str:
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    return _normalize_chassis_type(meta.get("chassis_type"))



def _device_freshness_tier(
    last_seen_at: Optional[str],
    *,
    stale_after_seconds: int,
    recent_after_seconds: int,
    now: Optional[datetime] = None,
) -> str:
    """UI: online | recent | stale | unknown."""
    silence = device_silence_status(
        last_seen_at, stale_after_seconds=stale_after_seconds, now=now
    )
    status = silence.get("status") or "unknown"
    if status == "unknown":
        return "unknown"
    if status == "stale":
        return "stale"
    seen = parse_utc(last_seen_at)
    if seen is None:
        return "unknown"
    clock = now or datetime.now(timezone.utc)
    age = max(0, int((clock - seen).total_seconds()))
    cap = badge_recent_after_seconds(recent_after_seconds, stale_after_seconds)
    return "online" if age <= cap else "recent"



def _freshness_limits(db: Database, settings: Settings) -> tuple[int, int]:
    stale = effective_stale_after_seconds(db, settings)
    recent = effective_recent_after_seconds(db)
    return stale, recent



def _chassis_map_for_devices(devices: list[dict]) -> dict[str, str]:
    return {str(d["bad_id"]): _chassis_type_from_device(d) for d in devices if d.get("bad_id")}



def _format_config_interval(value: object, empty: str = "—") -> str:
    """Числовой интервал настроек агента: -1 → «не задан»."""
    if value is None:
        return empty
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value)
    return "не задан" if n < 0 else str(n)



def _pager_items(current: object, total_pages: object) -> list:
    """Номера страниц и «…» для компактной пагинации списков."""
    cur = max(1, int(current or 1))
    pages = max(1, int(total_pages or 1))
    if pages <= 1:
        return []
    if pages <= 7:
        return list(range(1, pages + 1))
    anchors = sorted(
        p
        for p in {1, pages, cur, cur - 1, cur + 1}
        if 1 <= p <= pages
    )
    out: list = []
    prev = 0
    for p in anchors:
        if prev and p - prev > 1:
            out.append("…")
        out.append(p)
        prev = p
    return out



def _pager_url(
    base_path: str,
    page: int,
    *,
    q: str = "",
    tag: str = "",
    wave: str = "",
    archive: bool = False,
    bad_id: str = "",
    importance: str = "",
    event_type: str = "",
    date_from: str = "",
    date_to: str = "",
    os: str = "",
    ram: str = "",
    disk: str = "",
    cpu: str = "",
    cpu_vendor: str = "",
    agent: str = "",
    fresh: str = "",
    model: str = "",
    chassis: str = "",
    auth: str = "",
) -> str:
    """URL списка с сохранением фильтров (серверная пагинация ?page=)."""
    params: dict[str, str] = {}
    if bad_id:
        params["bad_id"] = bad_id
    if q:
        params["q"] = q
    if tag:
        params["tag"] = tag
    if wave:
        params["wave"] = wave
    if archive:
        params["archive"] = "1"
    if os:
        params["os"] = os
    if ram:
        params["ram"] = ram
    if disk:
        params["disk"] = disk
    if cpu:
        params["cpu"] = cpu
    if cpu_vendor:
        params["cpu_vendor"] = cpu_vendor
    if agent:
        params["agent"] = agent
    if fresh:
        params["fresh"] = fresh
    if model:
        params["model"] = model
    if chassis:
        params["chassis"] = chassis
    if auth:
        params["auth"] = auth
    if importance:
        params["importance"] = importance
    if event_type:
        params["type"] = event_type
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    if page > 1:
        params["page"] = str(page)
    qs = urlencode(params)
    return f"{base_path}?{qs}" if qs else base_path


_FLEET_SNAPSHOT_TTL_SEC = 8.0

_fleet_snapshot_cache: dict[str, Any] = {"ts": 0.0, "data": None}



def _invalidate_fleet_snapshot_cache() -> None:
    _fleet_snapshot_cache["data"] = None
    _fleet_snapshot_cache["ts"] = 0.0



def _fleet_snapshot(
    db: Database, settings: Settings
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Один проход fleet + stats + ops для Обзора и Дашборда."""
    now = time.monotonic()
    cached = _fleet_snapshot_cache
    if cached["data"] is not None and (now - float(cached["ts"])) < _FLEET_SNAPSHOT_TTL_SEC:
        return cached["data"]
    stale_sec = effective_stale_after_seconds(db, settings)
    active, archived = db.list_fleet_active_archived()
    hidden = {str(item) for item in db.approved_enrollment_bad_ids() if item}
    if hidden:
        active = [
            d for d in active if str(d.get("bad_id") or "") not in hidden
        ]
    stats = db.overview_stats(
        stale_after_seconds=stale_sec,
        active=active,
        archived=archived,
    )
    ops = ops_update_signals(
        db,
        stale_after_seconds=stale_sec,
        active=active,
    )
    ops = enrich_overview_ops_signals(db, ops)
    result = (active, archived, stats, ops)
    cached["data"] = result
    cached["ts"] = now
    return result
