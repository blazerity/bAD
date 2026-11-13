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

from .web_common import (
    _chassis_map_for_devices,
    _chassis_type_from_device,
    _device_freshness_tier,
    _fleet_snapshot,
    _format_chassis,
    _freshness_limits,
    _invalidate_fleet_snapshot_cache,
)

from .web_devices import (
    _devices_catalog_filter_options,
    _enrich_device_row,
)

router = APIRouter(tags=["web"], dependencies=[Depends(ensure_csrf)])




@router.get("/overview/search.json")
def overview_search_json(
    q: str = Query(default="", max_length=128),
    limit: int = Query(default=30, ge=1, le=50),
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    """Глобальный поиск Обзора: устройства + события (сессия)."""
    del user
    del limit
    query = (q or "").strip()
    if len(query) < 2:
        return JSONResponse({"devices": [], "events": [], "users": []})
    devices = db.search_devices_global(query, limit=8)
    dev_out = [_short_search_device(d, query) for d in devices]
    return JSONResponse({"devices": dev_out, "q": query})



def _short_search_device(device: dict, query: str) -> dict[str, str]:
    did = str(device.get("bad_id") or "")
    host = str(device.get("hostname") or "")
    shown = host or did
    label, value = device_match_parts(device, query)
    if host and query.casefold() in host.casefold():
        title = highlight_match(host, query)
    else:
        title = highlight_match(shown, "")
    return {
        "href": f"/devices/{did}",
        "hostname": shown,
        "match_reason": label,
        "title_html": title,
        "match_label": label,
        "match_html": highlight_match(value, query) if label and value else "",
    }



_EXPANDED_PAGE = 20

_FILTER_KEYS = ("os", "ram", "disk", "cpu", "model", "chassis")



@router.get("/overview/search/expanded.json")
def overview_search_expanded_json(
    q: str = Query(default="", max_length=128),
    offset: int = Query(default=0, ge=0),
    os: Optional[str] = None,
    ram: Optional[str] = None,
    disk: Optional[str] = None,
    cpu: Optional[str] = None,
    model: Optional[str] = None,
    chassis: Optional[str] = None,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    del user
    query = (q or "").strip()
    if len(query) < 2:
        return JSONResponse(
            {
                "devices": [],
                "events": [],
                "more_devices": False,
                "more_events": False,
            }
        )
    os_filter = (os or "").strip() or None
    ram_filter = (ram or "").strip() or None
    disk_filter = (disk or "").strip() or None
    cpu_filter = (cpu or "").strip() or None
    model_filter = (model or "").strip() or None
    chassis_filter = (chassis or "").strip().casefold() or None
    if chassis_filter and chassis_filter not in {"laptop", "desktop", "server", "vm", "other"}:
        chassis_filter = None
    start = max(0, int(offset))
    hits = db.search_devices_global(
        query, limit=start + _EXPANDED_PAGE * 3
    )
    narrowed = []
    for device in hits:
        meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
        if meta_facet_matches(
            meta,
            device,
            os_filter=os_filter,
            ram_filter=ram_filter,
            disk_filter=disk_filter,
            cpu_filter=cpu_filter,
            model_filter=model_filter,
            chassis_filter=chassis_filter,
        ):
            narrowed.append(device)
    page = narrowed[start : start + _EXPANDED_PAGE]
    stale, recent = _freshness_limits(db, settings)
    devices_out = []
    for device in page:
        enriched = _enrich_device_row(
            device,
            stale_after_seconds=stale,
            recent_after_seconds=recent,
        )
        meta = enriched.get("meta") if isinstance(enriched.get("meta"), dict) else {}
        row = _short_search_device(enriched, query)
        ips = enriched.get("ip_addresses") or []
        os_text = str(enriched.get("os_display") or "")
        devices_out.append(
            {
                "href": row["href"],
                "hostname": row["hostname"],
                "title_html": row["title_html"],
                "match_label": row["match_label"],
                "match_html": row["match_html"],
                "model": str(meta.get("hardware_model") or "").strip(),
                "user": str(enriched.get("user_display_name") or "").strip(),
                "os": "" if os_text.strip() in {"", "—"} else os_text,
                "ip": str(ips[0]).strip() if ips else "",
            }
        )
    events = db.list_device_events(
        q=query,
        importance="all",
        include_detail=False,
        limit=_EXPANDED_PAGE,
        offset=start,
    )
    events_out = []
    for event in events:
        eid = int(event["id"])
        events_out.append(
            {
                "href": f"/events/{eid}",
                "title_html": highlight_match(event.get("summary") or "", query),
                "match_label": event_match_label(event, query),
                "hostname": str(event.get("hostname") or ""),
                "created_at": event.get("created_at") or "",
            }
        )
    payload: dict[str, Any] = {
        "devices": devices_out,
        "events": events_out,
        "more_devices": len(page) == _EXPANDED_PAGE,
        "more_events": len(events) == _EXPANDED_PAGE,
    }
    if start == 0:
        active, _archived, stats, ops = _fleet_snapshot(db, settings)
        dashboard = build_dashboard_stats(
            db,
            stale_after_seconds=effective_stale_after_seconds(db, settings),
            stats=stats,
            active=active,
            ops=ops,
        )
        catalog = _devices_catalog_filter_options(active, dashboard, stats)
        payload["filters"] = {key: list(catalog.get(key) or []) for key in _FILTER_KEYS}
    return JSONResponse(payload)



@router.get("/devices/search.json")
def devices_search_json(
    q: str = Query(default="", max_length=128),
    limit: int = Query(default=25, ge=1, le=50),
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    """Быстрый поиск устройств для live UI (сессия, не admin Bearer)."""
    del user
    query = (q or "").strip()
    if len(query) < 1:
        return JSONResponse({"devices": []})
    cap = max(1, min(int(limit or 25), 50))
    rows = (
        db.search_devices_global(query, limit=cap)
        if len(query) >= 2
        else db.list_devices(archived=False, q=query, limit=cap)
    )
    payloads = (
        db.latest_inventory_payloads(
            [str(d.get("bad_id") or "") for d in rows],
            cap=max(len(rows), 1),
        )
        if len(query) >= 2
        else {}
    )
    out = []
    for d in rows:
        label = d.get("hostname") or d["bad_id"]
        hw = None
        payload = payloads.get(str(d.get("bad_id") or ""))
        if isinstance(payload, dict):
            raw_hw = payload.get("hardware")
            hw = raw_hw if isinstance(raw_hw, dict) else None
        reason = device_match_label(d, query, hardware=hw)
        meta_line = matched_serial_subtitle(d, query, hardware=hw) or reason
        out.append(
            {
                "bad_id": d["bad_id"],
                "hostname": label,
                "href": f"/devices/{d['bad_id']}",
                "chassis_type": _chassis_type_from_device(d),
                "chassis_label": _format_chassis(_chassis_type_from_device(d)),
                "match_reason": reason,
                "title_html": highlight_match(label, query),
                "subtitle_html": highlight_match(meta_line, query),
            }
        )
    return JSONResponse({"devices": out})
