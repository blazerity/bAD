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

router = APIRouter(tags=["web"], dependencies=[Depends(ensure_csrf)])




def _normalize_overview_priority_feed(
    events: list[dict[str, Any]],
    *,
    limit: int = 7,
) -> list[dict[str, Any]]:
    """Схлопнуть disk_added+disk_removed на одном ПК (~5 мин) → «Изменение диска»."""
    disk_pair = {"disk_added", "disk_removed"}
    window = 300  # секунд
    used: set[int] = set()
    out: list[dict[str, Any]] = []
    indexed = list(enumerate(events))
    for i, ev in indexed:
        if i in used or not isinstance(ev, dict):
            continue
        etype = str(ev.get("type") or "")
        did = str(ev.get("bad_id") or "")
        ts = parse_iso(ev.get("created_at"))
        merged = dict(ev)
        if etype in disk_pair and did and ts is not None:
            partner_idx = None
            want = "disk_added" if etype == "disk_removed" else "disk_removed"
            for j, other in indexed:
                if j <= i or j in used or not isinstance(other, dict):
                    continue
                if str(other.get("bad_id") or "") != did:
                    continue
                if str(other.get("type") or "") != want:
                    continue
                ots = parse_iso(other.get("created_at"))
                if ots is None:
                    continue
                if abs((ts - ots).total_seconds()) <= window:
                    partner_idx = j
                    break
            if partner_idx is not None:
                used.add(partner_idx)
                partner = events[partner_idx]
                merged["type"] = "disk_change"
                merged["importance"] = "medium"
                bits = [
                    str(x.get("summary") or "").strip()
                    for x in (ev, partner)
                    if str(x.get("summary") or "").strip()
                ]
                merged["summary"] = " · ".join(bits) if bits else "Изменение конфигурации диска"
        used.add(i)
        if "importance" not in merged or not merged.get("importance"):
            merged["importance"] = event_importance(str(merged.get("type") or ""))
        out.append(merged)
        if len(out) >= limit:
            break
    return out



_OVERVIEW_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "offline": 4}



def _overview_feed_event_rows(
    db: Database,
    fleet_by_id: dict[str, dict[str, Any]],
    *,
    limit: int = 80,
) -> list[dict[str, Any]]:
    """Строки для «Сейчас требует действия»: только критичные и высокие (без «шума» inventory)."""
    out: list[dict[str, Any]] = []
    for e in db.list_device_events(importance="all", limit=limit, include_detail=False):
        if not isinstance(e, dict):
            continue
        imp = event_importance(str(e.get("type") or ""))
        if imp not in ("critical", "high"):
            continue
        did = str(e.get("bad_id") or "")
        dev = fleet_by_id.get(did) or {}
        host = str(dev.get("hostname") or dev.get("bad_id") or did or "—")
        eid = e.get("id")
        href = f"/events/{eid}" if eid is not None else "/events"
        out.append(
            {
                **dict(e),
                "importance": imp,
                "hostname": host,
                "href": href,
                "summary": str(e.get("summary") or e.get("type") or ""),
            }
        )
    return out



def _overview_action_rows(
    attention: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    *,
    limit: int = 48,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for a in attention:
        aid = str(a.get("id") or "")
        sev = "offline" if aid == "stale" else str(a.get("severity") or "high")
        rows.append(
            {
                "severity": sev,
                "hostname": "Панель",
                "summary": str(a.get("title") or ""),
                "detail": str(a.get("detail") or ""),
                "href": str(a.get("href") or "#"),
                "created_at": "",
                "sort_time": "",
            }
        )
    for e in event_rows:
        if e.get("severity"):
            rows.append(
                {
                    "severity": str(e.get("severity") or "low"),
                    "hostname": str(e.get("hostname") or "—"),
                    "summary": str(e.get("summary") or ""),
                    "detail": str(e.get("detail") or ""),
                    "href": str(e.get("href") or "#"),
                    "created_at": str(e.get("created_at") or ""),
                    "sort_time": str(e.get("created_at") or ""),
                }
            )
            continue
        imp = str(e.get("importance") or "low")
        rows.append(
            {
                "severity": imp,
                "hostname": str(e.get("hostname") or "—"),
                "summary": str(e.get("summary") or e.get("type") or ""),
                "detail": "",
                "href": str(e.get("href") or "#"),
                "created_at": str(e.get("created_at") or ""),
                "sort_time": str(e.get("created_at") or ""),
            }
        )

    def _sort_key(row: dict[str, Any]) -> tuple[int, str]:
        return (
            _OVERVIEW_SEV_ORDER.get(str(row.get("severity") or ""), 9),
            str(row.get("sort_time") or ""),
        )

    rows.sort(key=_sort_key, reverse=True)
    rows.sort(key=lambda r: _OVERVIEW_SEV_ORDER.get(str(r.get("severity") or ""), 9))
    return rows[:limit]



def _overview_page_context(
    *,
    user: WebUser,
    db: Database,
    settings: Settings,
) -> dict[str, Any]:
    """SSR context Обзора — Command Center (оперативный пульт)."""
    active, _archived, stats, ops = _fleet_snapshot(db, settings)
    security = security_status(db, settings)
    ops = merge_security_into_ops(ops, security)
    wave = build_wave_counts(
        active, ops=ops, stale_n=int(stats.get("stale") or 0)
    )
    ops["wave_counts"] = {
        "drift": wave["drift"],
        "revoked": wave["revoked"],
        "agent_local": wave["agent_local"],
        "stale": wave["stale"],
    }
    ops["wave_chips"] = wave["chips"]
    ops["agent_local_count"] = wave["agent_local"]
    tls_mode = str(ops.get("tls_mode") or tls_panel_mode() or "http")
    bootstrap = build_bootstrap_checklist(
        user=user,
        db=db,
        settings=settings,
        ops=ops,
        active_devices=int(stats.get("total_active") or 0),
        security=security,
    )
    bootstrap_progress = build_bootstrap_progress(
        user=user,
        ops=ops,
        active_devices=int(stats.get("total_active") or 0),
        security=security,
        settings=settings,
    )
    chassis_by_id = _chassis_map_for_devices(active)
    fleet_by_id = {str(d["bad_id"]): d for d in active if d.get("bad_id")}
    for d in ops.get("version_drift") or []:
        if isinstance(d, dict):
            d["chassis_type"] = chassis_by_id.get(str(d.get("bad_id") or ""), "other")
    raw_feed: list[dict[str, Any]] = []
    for e in stats.get("recent_hardware_events") or []:
        if not isinstance(e, dict):
            continue
        did = str(e.get("bad_id") or "")
        e = dict(e)
        e["chassis_type"] = chassis_by_id.get(did, "other")
        dev = fleet_by_id.get(did) or {}
        e["bad_id"] = dev.get("bad_id")
        e["device_href"] = f"/devices/{did}"
        e["importance"] = event_importance(str(e.get("type") or ""))
        raw_feed.append(e)
    # Берём больше сырых строк, чтобы после схлопывания осталось 7
    if len(raw_feed) < 16:
        extra = db.list_device_events(importance="high", limit=24, include_detail=False)
        seen_ids = {int(x.get("id") or 0) for x in raw_feed}
        for e in extra:
            eid = int(e.get("id") or 0)
            if eid in seen_ids:
                continue
            did = str(e.get("bad_id") or "")
            e = dict(e)
            e["chassis_type"] = chassis_by_id.get(did, "other")
            dev = fleet_by_id.get(did) or {}
            e["bad_id"] = dev.get("bad_id")
            e["device_href"] = f"/devices/{did}"
            e["importance"] = event_importance(str(e.get("type") or ""))
            raw_feed.append(e)
            seen_ids.add(eid)
        raw_feed.sort(
            key=lambda x: (str(x.get("created_at") or ""), int(x.get("id") or 0)),
            reverse=True,
        )
    normalized = _normalize_overview_priority_feed(raw_feed, limit=40)
    priority_feed = aggregate_incident_feed(
        normalized, fleet_by_id, limit=10
    )
    feed_has_critical = any(
        str(e.get("importance") or "") == "critical" for e in priority_feed
    )
    attention = build_attention_queue(
        user=user,
        ops=ops,
        stats=stats,
        tls_mode=tls_mode,
        security=security,
    )
    server_current = server_read_current(releases_dir(settings))
    events_total = db.count_device_events(importance="all")
    critical_event_count = db.count_device_events_exact_importance("critical")
    high_event_count = db.count_device_events_exact_importance("high")
    medium_event_count = db.count_device_events_exact_importance("medium")
    low_event_count = db.count_device_events_exact_importance("low")
    offline_device_count = int(stats.get("stale") or 0)
    feed_event_rows = _overview_feed_event_rows(db, fleet_by_id)
    overview_action_rows = _overview_action_rows(attention, feed_event_rows)
    overview_sev_total = (
        critical_event_count
        + high_event_count
        + medium_event_count
        + low_event_count
        + offline_device_count
    )
    server_runtime = build_server_runtime(db)
    total_active = int(stats.get("total_active") or 0)
    drift_n = int(ops.get("version_drift_count") or 0)
    current_n = max(0, total_active - drift_n)
    update_progress_pct = (
        round(100.0 * current_n / total_active, 1) if total_active else 100.0
    )
    event_series = {
        "days_default": 14,
        "label": "Динамика событий",
        "series": {
            "7": db.count_events_by_utc_day(7),
            "14": db.count_events_by_utc_day(14),
            "30": db.count_events_by_utc_day(30),
        },
    }
    return {
        "user": user,
        "stats": stats,
        "events_total": events_total,
        "critical_event_count": critical_event_count,
        "high_event_count": high_event_count,
        "medium_event_count": medium_event_count,
        "low_event_count": low_event_count,
        "offline_device_count": offline_device_count,
        "overview_action_rows": overview_action_rows,
        "overview_sev_total": overview_sev_total,
        "server_runtime": server_runtime,
        "ops": ops,
        "security": security,
        "bootstrap": bootstrap,
        "bootstrap_progress": bootstrap_progress,
        "attention": attention,
        "stale_after_seconds": effective_stale_after_seconds(db, settings),
        "server_current": server_current,
        "wave_chips": wave["chips"],
        "priority_feed": priority_feed,
        "feed_has_critical": feed_has_critical,
        "event_series": event_series,
        "update_progress": {
            "current": current_n,
            "drift": drift_n,
            "total": total_active,
            "pct": update_progress_pct,
            "target_version": ops.get("latest_version") or "—",
        },
    }



@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _html(request, "overview.html", _overview_page_context(user=user, db=db, settings=settings))



@router.get("/overview", response_class=HTMLResponse)
def overview_alias(
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return home(request, user=user, db=db, settings=settings)



@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Отдельная вкладка Дашборд: конфигурация парка (не /v1)."""
    active, _archived, stats, ops = _fleet_snapshot(db, settings)
    security = security_status(db, settings)
    ops = merge_security_into_ops(ops, security)
    dashboard = build_dashboard_stats(
        db,
        stale_after_seconds=effective_stale_after_seconds(db, settings),
        stats=stats,
        active=active,
        ops=ops,
    )
    return _html(
        request,
        "dashboard.html",
        {
            "user": user,
            "stats": stats,
            "ops": ops,
            "security": security,
            "dashboard": dashboard,
            "stale_after_seconds": effective_stale_after_seconds(db, settings),
        },
    )



@router.get("/setup/progress.json")
def setup_progress_json(
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """U5: явный прогресс мастера (шаг 1/2/3) для UI без своих эвристик."""
    _active, _archived, stats, ops = _fleet_snapshot(db, settings)
    security = security_status(db, settings)
    ops = merge_security_into_ops(ops, security)
    progress = build_bootstrap_progress(
        user=user,
        ops=ops,
        active_devices=int(stats.get("total_active") or 0),
        security=security,
        settings=settings,
    )
    return JSONResponse({"progress": progress})
