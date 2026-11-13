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



# RU-подписи type для ленты (inventory-plus + уже известные).
_EVENT_TYPE_LABELS_RU = {
    "last_boot_change": "Перезагрузка",
    "pending_reboot_change": "Ожидание перезагрузки",
    "timezone_change": "Часовой пояс",
    "chassis_type_change": "Тип корпуса",
    "tpm_change": "TPM",
    "secure_boot_change": "Secure Boot",
    "antivirus_change": "Антивирус",
    "minidump_bugcheck": "BSOD / bugcheck",
    "disk_added": "Диск добавлен",
    "disk_removed": "Диск удалён",
    "disk_change": "Изменение диска",
    "hostname_change": "Hostname",
    "agent_version_change": "Версия агента",
    "os_build_change": "Сборка Windows",
    "ad_ou_change": "OU",
    "bios_update": "BIOS",
    "smbios_uuid_change": "SMBIOS UUID",
    "baseboard_serial_change": "Серийник платы",
    "bios_serial_change": "Серийник BIOS",
    "gpu_added": "Видеокарта подключена",
    "gpu_removed": "Видеокарта отключена",
    "monitor_set_change": "Мониторы",
    "nic_mac_change": "Сетевой интерфейс",
    "domain_change": "Домен",
    "serial_change": "Серийный номер",
    "model_change": "Модель",
    "manufacturer_change": "Производитель",
    "cpu_change": "Процессор",
    "ram_bytes_change": "ОЗУ",
    "ram_module_added": "Планка ОЗУ+",
    "ram_module_removed": "Планка ОЗУ−",
    "volume_free_drop": "Свободное место",
    "volume_free_critical": "Мало места на диске",
    "nic_ipv4_change": "IPv4",
    "logged_on_change": "Пользователи",
    "last_interactive_change": "Интерактивный вход",
    "usb_added": "USB подключено",
    "usb_removed": "USB отключено",
    "device_merged": "Объединение",
    "device_enrolled": "Регистрация устройства",
    "device_stale": "Устройство устарело",
    "device_back_online": "Снова на связи",
}



def _format_event_type(value: object, empty: str = "") -> str:
    if value is None:
        return empty
    key = str(value).strip()
    if not key:
        return empty
    return _EVENT_TYPE_LABELS_RU.get(key, key)



def _event_summary_anchor_hostname(summary: object, hostname: object) -> Markup:
    """Имя узла в сводке — один визуальный токен (дефис не место переноса)."""
    text = str(summary) if summary is not None else ""
    host = str(hostname).strip() if hostname is not None else ""
    if not text or not host:
        return Markup(html.escape(text))
    pattern = re.escape(host)
    if not re.search(pattern, text):
        return Markup(html.escape(text))
    out: list[str] = []
    pos = 0
    for m in re.finditer(pattern, text):
        out.append(html.escape(text[pos : m.start()]))
        out.append(f'<span class="event-host-token">{html.escape(m.group(0))}</span>')
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return Markup("".join(out))


_MONTH_NAMES_RU = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)



def _day_heading_ru(day_key: object, *, today_utc: str, yesterday_utc: str) -> str:
    """Русская подпись дня для групп событий (UTC-ключ YYYY-MM-DD из web)."""
    key = str(day_key or "").strip()
    if not key:
        return ""
    if key == str(today_utc):
        return "Сегодня"
    if key == str(yesterday_utc):
        return "Вчера"
    parts = key.split("-")
    if len(parts) != 3:
        return key
    try:
        y, m, d = (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return key
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return key
    return f"{d} {_MONTH_NAMES_RU[m]} {y}"



def _importance_label_ru(level: object, empty: str = "") -> str:
    if level is None:
        return empty
    return IMPORTANCE_LABELS_RU.get(str(level), str(level))

EVENTS_PAGE_SIZE = 50



@router.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail_page(
    request: Request,
    event_id: int,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    event = db.get_device_event(event_id)
    if not event:
        return _html(
            request,
            "event_missing.html",
            {"user": user, "event_id": event_id},
            status_code=404,
        )
    from .smtp_mail import event_visual

    bad_id = str(event.get("bad_id") or "")
    chassis = "other"
    user_display_name = None
    user_presence = ""
    user_presence_caption = ""
    hardware_model = None
    hardware_manufacturer = None
    device_detail = None
    if bad_id:
        device_detail = db.get_device_detail(bad_id)
        if device_detail:
            chassis = _chassis_type_from_device(device_detail)
            device_meta = (
                device_detail.get("meta")
                if isinstance(device_detail.get("meta"), dict)
                else {}
            )
            presence = str(device_meta.get("user_presence") or "")
            if presence == "online":
                user_names = normalize_logged_on_list(device_meta.get("logged_on"))
                user_display_name = user_names[0] if user_names else None
                user_presence = "online"
                user_presence_caption = "в системе"
            else:
                user_display_name = device_meta.get("last_logged_on") or None
                user_presence = "last" if user_display_name else ""
                user_presence_caption = (
                    "последний" if user_display_name else ""
                )
            hw_model = device_meta.get("hardware_model")
            if hw_model:
                hardware_model = str(hw_model).strip()
            hw_mfr = device_meta.get("hardware_manufacturer")
            if hw_mfr:
                hardware_manufacturer = str(hw_mfr).strip()
    visual = event_visual(str(event.get("type") or ""))
    if visual.get("icon") == "host":
        visual = {**visual, "icon": "devices"}
    permalink = f"/events/{event_id}"
    detail = event.get("detail")
    detail_pretty = (
        json.dumps(detail, ensure_ascii=False, indent=2)
        if detail
        else None
    )
    return _html(
        request,
        "event_detail.html",
        {
            "user": user,
            "event": event,
            "visual": visual,
            "chassis_type": chassis,
            "permalink": permalink,
            "detail_pretty": detail_pretty,
            "user_display_name": user_display_name,
            "user_presence": user_presence,
            "user_presence_caption": user_presence_caption,
            "hardware_model": hardware_model,
            "hardware_manufacturer": hardware_manufacturer,
        },
    )



@router.get("/events", response_class=HTMLResponse)
def events_page(
    request: Request,
    bad_id: Optional[str] = None,
    q: Optional[str] = None,
    importance: Optional[str] = None,
    type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    device_filter = (bad_id or "").strip() or None
    q_filter = (q or "").strip() or None
    imp = (importance or "").strip().casefold() or None
    if imp == "default":
        imp = None
    type_filter = (type or "").strip() or None
    date_from_f = (date_from or "").strip() or None
    date_to_f = (date_to or "").strip() or None
    page_i = max(1, int(page or 1))
    page_size = EVENTS_PAGE_SIZE
    count_kw = {
        "bad_id": device_filter,
        "q": q_filter,
        "importance": imp,
        "event_type": type_filter,
        "date_from": date_from_f,
        "date_to": date_to_f,
    }
    total = db.count_device_events(**count_kw)
    pages = max(1, (total + page_size - 1) // page_size)
    if page_i > pages:
        page_i = pages
    offset = (page_i - 1) * page_size
    events = db.list_device_events(
        bad_id=device_filter,
        limit=page_size,
        offset=offset,
        q=q_filter,
        importance=imp,
        event_type=type_filter,
        date_from=date_from_f,
        date_to=date_to_f,
        include_detail=False,
    )
    from .smtp_mail import event_visual

    chassis_by_id = _chassis_map_for_devices(db.list_devices(archived=None))
    for e in events:
        e["chassis_type"] = chassis_by_id.get(str(e.get("bad_id") or ""), "other")
        e["event_icon"] = event_visual(str(e.get("type") or "")).get("icon") or "events"
    today_d = datetime.now(timezone.utc).date()
    yesterday_d = today_d - timedelta(days=1)
    chip_kw = {
        "bad_id": device_filter,
        "q": q_filter,
        "event_type": type_filter,
        "date_from": date_from_f,
        "date_to": date_to_f,
    }
    event_filter_counts = {
        "default": db.count_device_events(**chip_kw, importance=None),
        "all": db.count_device_events(**chip_kw, importance="all"),
        "high": db.count_device_events(**chip_kw, importance="high"),
        "critical": db.count_device_events(**chip_kw, importance="critical"),
    }
    shown_total = total
    chip_narrow = None
    if imp:
        narrow_kw = {**count_kw, "importance": None}
        shown_total = db.count_device_events(**narrow_kw)
        p: dict[str, str] = {}
        if device_filter:
            p["bad_id"] = device_filter
        if q_filter:
            p["q"] = q_filter
        if type_filter:
            p["type"] = type_filter
        if date_from_f:
            p["date_from"] = date_from_f
        if date_to_f:
            p["date_to"] = date_to_f
        chip_narrow = "/events?" + urlencode(p) if p else "/events"
    return _html(
        request,
        "events.html",
        {
            "events": events,
            "user": user,
            "device_filter": device_filter or "",
            "q": q_filter or "",
            "importance": imp if imp else "",
            "event_type": type_filter or "",
            "date_from": date_from_f or "",
            "date_to": date_to_f or "",
            "page": page_i,
            "pages": pages,
            "total": total,
            "shown_total": shown_total,
            "chip_narrow_href": chip_narrow,
            "page_size": page_size,
            "today_utc": today_d.isoformat(),
            "yesterday_utc": yesterday_d.isoformat(),
            "event_filter_counts": event_filter_counts,
        },
    )
