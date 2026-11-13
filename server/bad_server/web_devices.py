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
from .event_importance import (
    FILTER_PRESET_LABELS_RU,
    IMPORTANCE_LABELS_RU,
    _EVENT_IMPORTANCE,
    event_importance,
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
    _CHASSIS_LABELS_RU,
    _chassis_map_for_devices,
    _chassis_type_from_device,
    _device_freshness_tier,
    _fleet_snapshot,
    _format_bytes,
    _format_chassis,
    _format_os,
    _freshness_limits,
    _invalidate_fleet_snapshot_cache,
    _normalize_chassis_type,
)

from .web_settings import (
    _settings_raw_from_form,
    _validate_update_target_pin,
)

router = APIRouter(tags=["web"], dependencies=[Depends(ensure_csrf)])

DEVICES_PAGE_SIZE = 50


_PANEL_CSS_PATH = panel_root() / "static" / "style.css"

_panel_css_cache: Optional[str] = None


_REBOOT_REASON_LABELS_RU = {
    "windows_update": "Центр обновления Windows",
    "cbs": "обслуживание компонентов",
}


_DISK_ROLE_LABELS_RU = {
    "flash": "флешка",
    "usb_disk": "USB-диск",
    "fixed": "диск",
}



def _disk_role_label_ru(disk: object) -> str:
    if not isinstance(disk, dict):
        return "диск"
    role = disk_role(disk)
    return _DISK_ROLE_LABELS_RU.get(role, role)



def _pending_reboot_visible(host_info: Optional[dict]) -> bool:
    if not isinstance(host_info, dict):
        return False
    if host_info.get("pending_reboot") is not True:
        return False
    reasons = host_info.get("pending_reboot_reasons")
    return isinstance(reasons, list) and bool(reasons)


# Панели карточки: overview/config/admin/events + inventory ids при наличии данных.
DEVICE_FIXED_VIEWS = frozenset({"overview", "config", "admin", "events", "chassis"})



def _device_inventory_nav(
    *,
    host_info: Optional[dict],
    hardware_summary: Optional[dict],
    network_info: Optional[dict],
    users_info: Optional[dict],
    software_info: Optional[dict],
    minidumps_info: Optional[dict],
    collector_errors: Optional[list],
    security_info: Optional[dict] = None,
    device_meta: Optional[dict] = None,
    device_baseboard_serial: Optional[str] = None,
    keep_empty: bool = False,
) -> list[dict]:
    """Пункты Speccy-навигации + краткие строки для Обзора.

    По умолчанию одна самая важная строка на характеристику.
    Две — только если в одну никак или единиц две (диски / планки / GPU).
    """
    hw = hardware_summary if isinstance(hardware_summary, dict) else None
    items: list[dict] = []

    def add(view_id: str, icon: str, title: str, lines: list[str]) -> None:
        cleaned = [ln for ln in lines if ln]
        items.append(
            {
                "id": view_id,
                "icon": icon,
                "title": title,
                "lines": cleaned[:2],
            }
        )

    def _disk_overview_line(disk: dict) -> str:
        bits = [disk.get("model") or "диск", _format_bytes(disk.get("size_bytes"))]
        if disk.get("interface_type"):
            bits.append(str(disk.get("interface_type")))
        # serial — в разделе Накопители, не в Обзоре
        return " · ".join(str(x) for x in bits if x and x != "—")

    if host_info is not None:
        os_line = _format_os(host_info.get("os"))
        # boot / pending reboot / timezone — одна строка вместе с ОС
        status = ""
        if _pending_reboot_visible(host_info):
            status = "ожидает перезагрузку"
        elif host_info.get("last_boot_at"):
            status = f"загрузка {host_info.get('last_boot_at')}"
        elif host_info.get("timezone"):
            status = str(host_info.get("timezone"))
        add(
            "os",
            "host",
            "Операционная система",
            [" · ".join(x for x in (os_line, status) if x)],
        )
    elif keep_empty:
        add("os", "host", "Операционная система", [])

    cpu_present = isinstance(hw, dict) and "cpu" in hw and hw.get("cpu") is not None
    if cpu_present:
        cpu = hw["cpu"] if isinstance(hw["cpu"], dict) else {}
        name = str(cpu.get("name") or "").strip() or "CPU"
        cores = cpu.get("cores")
        logical = cpu.get("logical")
        if cores is not None or logical is not None:
            c = cores if cores is not None else "-"
            lg = logical if logical is not None else "-"
            name = f"{name} · {c}/{lg}"
        add("cpu", "cpu", "Процессор", [name])
    elif keep_empty:
        add("cpu", "cpu", "Процессор", [])

    board_serial = str(device_baseboard_serial or "").strip()
    mb_ready = bool(
        hw
        and (
            hw.get("manufacturer")
            or hw.get("model")
            or hw.get("serial_number")
            or hw.get("bios_version")
            or hw.get("bios_manufacturer")
            or hw.get("bios_release_date")
            or hw.get("baseboard_serial")
        )
    )
    if mb_ready:
        # serial платы — в разделе, не в Обзоре
        model_line = " · ".join(
            str(x) for x in (hw.get("manufacturer"), hw.get("model")) if x
        )
        add(
            "mb",
            "model",
            "Материнская плата",
            [model_line or str(hw.get("serial_number") or "плата")],
        )
    elif board_serial:
        add("mb", "model", "Материнская плата", [board_serial])
    elif keep_empty:
        add("mb", "model", "Материнская плата", [])

    if hw and (
        hw.get("ram_bytes") is not None
        or hw.get("ram_memory_type")
        or hw.get("ram_modules")
    ):
        ram = _format_bytes(hw.get("ram_bytes"))
        dtype = hw.get("ram_memory_type") or ""
        modules = hw.get("ram_modules") or []
        line1 = " · ".join(
            x for x in ((ram if ram != "—" else ""), str(dtype)) if x
        ) or "ОЗУ"
        if len(modules) >= 2:
            # две планки → допускается вторая строка
            add(
                "memory",
                "ram",
                "Память",
                [line1, f"{len(modules)} планок"],
            )
        else:
            if len(modules) == 1:
                line1 = f"{line1} · 1 планка" if line1 != "ОЗУ" else "1 планка"
            add("memory", "ram", "Память", [line1])
    elif keep_empty:
        add("memory", "ram", "Память", [])

    if hw and hw.get("gpus"):
        gpus = hw["gpus"]
        lines: list[str] = []
        for g in gpus[:2]:
            if isinstance(g, dict) and g.get("name"):
                lines.append(str(g.get("name")))
            elif isinstance(g, dict):
                lines.append(str(g.get("vendor") or "GPU"))
        if len(gpus) > 2:
            lines = [lines[0], f"+{len(gpus) - 1} ещё"]
        add("gpu", "gpu", "Видео", lines or ["GPU"])
    elif keep_empty:
        add("gpu", "gpu", "Видео", [])

    has_storage = bool(hw and (hw.get("disks") or hw.get("volumes")))
    chassis_only = bool(hw and hw.get("chassis_type") and not has_storage)
    if chassis_only:
        chassis = _format_chassis(hw.get("chassis_type"))
        add(
            "chassis",
            "desktop",
            "Корпус",
            [chassis] if chassis else ["—"],
        )
    elif keep_empty and not has_storage:
        add("chassis", "desktop", "Корпус", [])

    if has_storage:
        disks = [d for d in (hw.get("disks") or []) if isinstance(d, dict)]
        volumes = hw.get("volumes") or []
        if len(disks) >= 2:
            add(
                "storage",
                "disk",
                "Накопители",
                [_disk_overview_line(disks[0]), _disk_overview_line(disks[1])],
            )
        elif disks:
            add("storage", "disk", "Накопители", [_disk_overview_line(disks[0])])
        elif volumes:
            add(
                "storage",
                "disk",
                "Накопители",
                [f"{len(volumes)} том(ов)"],
            )
    elif keep_empty:
        add("storage", "disk", "Накопители", [])

    if hw and hw.get("monitors"):
        mons = [m for m in hw["monitors"] if isinstance(m, dict)]
        lines = []
        for m in mons[:2]:
            label = str(m.get("name") or m.get("manufacturer") or "монитор")
            if m.get("width") and m.get("height"):
                label = f"{label} · {m['width']}×{m['height']}"
            lines.append(label)
        if len(mons) > 2:
            lines = [lines[0], f"+{len(mons) - 1} ещё"]
        add("monitors", "monitor", "Мониторы", lines)
    elif keep_empty:
        add("monitors", "monitor", "Мониторы", [])

    battery_present = isinstance(hw, dict) and "battery" in hw and hw.get("battery") is not None
    if battery_present:
        bat = hw["battery"] if isinstance(hw["battery"], dict) else {}
        charge = bat.get("charge_percent")
        if charge is not None:
            line = f"{charge}%"
            if bat.get("status"):
                line = f"{line} · {bat.get('status')}"
        else:
            line = str(bat.get("status") or "батарея")
        add("battery", "battery", "Батарея", [line])
    elif keep_empty:
        add("battery", "battery", "Батарея", [])

    if network_info and network_info.get("nics"):
        nics = [n for n in network_info["nics"] if isinstance(n, dict)]
        lines = []
        for n in nics[:2]:
            ipv4 = n.get("ipv4") or []
            ip = ipv4[0] if ipv4 else (n.get("mac") or "")
            name = str(n.get("name") or "NIC")
            lines.append(" · ".join(x for x in (name, str(ip)) if x))
        if len(nics) > 2:
            lines = [lines[0], f"+{len(nics) - 1} ещё"]
        add("network", "network", "Сеть", lines)
    elif keep_empty:
        add("network", "network", "Сеть", [])

    meta = device_meta if isinstance(device_meta, dict) else {}
    presence = str(meta.get("user_presence") or "")
    if presence == "online":
        who = format_logged_on_display(meta.get("logged_on"))[:80]
    else:
        who = str(meta.get("last_logged_on") or "").strip()
    if not who and users_info:
        who = normalize_logged_on_user(users_info.get("last_interactive")) or (
            format_logged_on_display(users_info.get("logged_on"))[:80]
        )
    add("users", "users", "Пользователи", [who if who else "нет данных"])

    if software_info is not None:
        programs = software_info.get("programs")
        if programs is None:
            line1 = "недоступно"
        else:
            line1 = f"{len(programs)} программ"
        add("software", "software", "ПО", [line1])
    elif keep_empty:
        add("software", "software", "ПО", [])

    sec = security_info if isinstance(security_info, dict) else None
    sec_ready = bool(
        sec and (
        sec.get("tpm_present") is not None
        or sec.get("secure_boot") is not None
        or sec.get("antivirus")
        or sec.get("tpm_spec_version")
    )
    )
    if sec_ready:
        # одна строка в Обзоре; детали TPM/SB/AV — в разделе Безопасность
        av_names: list[str] = []
        for item in sec.get("antivirus") or []:
            if isinstance(item, dict) and item.get("name"):
                av_names.append(str(item["name"]))
            elif isinstance(item, str) and item.strip():
                av_names.append(item.strip())
        if av_names:
            line = av_names[0]
            if len(av_names) > 1:
                line = f"{line} +{len(av_names) - 1}"
        elif sec.get("tpm_present") is True:
            line = "TPM есть"
            if sec.get("tpm_spec_version"):
                line = f"{line} · {sec.get('tpm_spec_version')}"
        elif sec.get("tpm_present") is False:
            line = "TPM нет"
        elif sec.get("secure_boot") is True:
            line = "Secure Boot вкл"
        elif sec.get("secure_boot") is False:
            line = "Secure Boot выкл"
        else:
            line = "security"
        add("security", "tls", "Безопасность", [line])
    elif keep_empty:
        add("security", "tls", "Безопасность", [])

    if minidumps_info is not None:
        # bugcheck — в Событиях; в Обзоре максимум одна строка при BSOD
        bug = ""
        for f in minidumps_info.get("files") or []:
            if isinstance(f, dict) and f.get("bugcheck_code"):
                bug = str(f.get("bugcheck_code"))
                msg = f.get("bugcheck_message")
                if msg:
                    bug = f"{bug} · {str(msg)[:40]}"
                break
        if bug:
            add("minidumps", "events", "Минидампы BSOD", [bug])
        else:
            count = minidumps_info.get("count")
            if count:
                add("minidumps", "events", "Минидампы BSOD", [f"{count} файлов"])
            elif minidumps_info.get("memory_dmp_present"):
                add("minidumps", "events", "Минидампы BSOD", ["Memory.dmp есть"])
            else:
                add("minidumps", "events", "Минидампы BSOD", ["нет дампов"])
    elif keep_empty:
        add("minidumps", "events", "Минидампы BSOD", [])

    if collector_errors:
        add("errors", "events", "Ошибки сбора", [f"{len(collector_errors)} ошибок"])

    return items



def _enrich_device_row(
    device: dict, *, stale_after_seconds: int, recent_after_seconds: int
) -> dict:
    device = dict(device)
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    device["silence"] = device_silence_status(
        device.get("last_seen_at"),
        stale_after_seconds=stale_after_seconds,
    )
    device["chassis_type"] = _chassis_type_from_device(device)
    device["chassis_label"] = _format_chassis(device["chassis_type"])
    device["freshness"] = _device_freshness_tier(
        device.get("last_seen_at"),
        stale_after_seconds=stale_after_seconds,
        recent_after_seconds=recent_after_seconds,
    )
    did = str(device.get("bad_id") or "")
    device["device_href"] = f"/devices/{did}"
    # Список: номинал ОЗУ (8/16/32…) + DDR; без «Майкрософт» в ОС.
    ram_list = meta.get("ram_list_display")
    if not ram_list:
        ram_list = format_ram_list_cell(
            meta.get("ram_bytes"),
            meta.get("ram_ddr") or meta.get("ram_memory_type"),
        )
    if not ram_list or ram_list == "—":
        ram_list = meta.get("ram_bucket") or meta.get("ram_display") or "—"
    device["ram_display"] = ram_list
    device["disk_display"] = meta.get("disk_bucket") or "—"
    raw_os = meta.get("os_caption") or meta.get("os") or ""
    device["os_display"] = normalize_os_caption(raw_os) if raw_os else "—"
    cpu_raw = meta.get("cpu_name")
    device["cpu_display"] = format_cpu_short(cpu_raw) if cpu_raw else "—"
    presence = str(meta.get("user_presence") or "")
    if presence == "online":
        names = normalize_logged_on_list(meta.get("logged_on"))
        device["user_display_name"] = names[0] if names else None
        device["user_presence"] = "online"
        device["user_presence_caption"] = "в системе"
    else:
        device["user_display_name"] = meta.get("last_logged_on") or None
        device["user_presence"] = "last" if device["user_display_name"] else ""
        device["user_presence_caption"] = "последний" if device["user_display_name"] else ""
    ips = meta.get("ipv4_addresses")
    if isinstance(ips, list) and ips:
        ip_list = [str(x).strip() for x in ips if x and str(x).strip()]
    else:
        ip_list = []
    device["ip_addresses"] = ip_list
    return device



def _facet_catalog_label_ok(label: str) -> bool:
    text = (label or "").strip()
    if not text or text == "—":
        return False
    low = text.casefold()
    if low in {"прочее", "другое", "other"}:
        return False
    if low.startswith("прочее"):
        return False
    return True



def _bar_chart_labels(bar: Optional[dict[str, Any]]) -> list[str]:
    if not isinstance(bar, dict):
        return []
    out: list[str] = []
    for row in bar.get("items") or []:
        if not isinstance(row, dict) or row.get("is_other"):
            continue
        label = str(row.get("label") or "").strip()
        if _facet_catalog_label_ok(label):
            out.append(label)
    return out



def _devices_catalog_filter_options(
    fleet: list[dict],
    dashboard: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, list[str]]:
    """Ярлыки фасетов как на дашборде + версии агента из парка."""
    cpu_block = dashboard.get("cpu_family_treemap") or {}
    cpu_vals: list[str] = []
    for item in cpu_block.get("items") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if _facet_catalog_label_ok(label):
            cpu_vals.append(label)
    vendor_vals: set[str] = set()
    model_vals: set[str] = set()
    chassis_present: set[str] = set()
    for d in fleet:
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        vendor = str(meta.get("cpu_vendor") or "").strip()
        if vendor and _facet_catalog_label_ok(vendor):
            vendor_vals.add(vendor)
        model = str(meta.get("hardware_model") or "").strip()
        if model and _facet_catalog_label_ok(model):
            model_vals.add(model)
        chassis = str(meta.get("chassis_type") or "").strip().casefold()
        if chassis in _CHASSIS_LABELS_RU:
            chassis_present.add(chassis)
    agent_vals: set[str] = set()
    for row in stats.get("agent_versions") or []:
        ver = str(row.get("version") or "").strip()
        if ver and ver != "—":
            agent_vals.add(ver)
    for d in fleet:
        ver = str(d.get("agent_version") or "").strip()
        if ver:
            agent_vals.add(ver)
    sort_key = lambda s: s.casefold()
    return {
        "os": _bar_chart_labels(dashboard.get("os_bars")),
        "ram": _bar_chart_labels(dashboard.get("ram_bars")),
        "disk": _bar_chart_labels(dashboard.get("storage_bars")),
        "cpu": sorted(set(cpu_vals), key=sort_key),
        "cpu_vendor": sorted(vendor_vals, key=sort_key),
        "agent": sorted(agent_vals, key=sort_key),
        "model": sorted(model_vals, key=sort_key),
        "chassis": [key for key in _CHASSIS_LABELS_RU if key in chassis_present],
    }



def _devices_query_params(
    *,
    tag: Optional[str],
    q: Optional[str],
    archive: bool,
    page: int,
    wave: Optional[str] = None,
    os_filter: Optional[str] = None,
    ram_filter: Optional[str] = None,
    disk_filter: Optional[str] = None,
    cpu_filter: Optional[str] = None,
    cpu_vendor_filter: Optional[str] = None,
    agent_filter: Optional[str] = None,
    fresh: Optional[str] = None,
    model_filter: Optional[str] = None,
    chassis_filter: Optional[str] = None,
    sort: str = "",
    order: str = "",
) -> str:
    params: dict[str, str] = {}
    if tag:
        params["tag"] = tag
    if q:
        params["q"] = q
    if archive:
        params["archive"] = "1"
    if wave:
        params["wave"] = wave
    if os_filter:
        params["os"] = os_filter
    if ram_filter:
        params["ram"] = ram_filter
    if disk_filter:
        params["disk"] = disk_filter
    if cpu_filter:
        params["cpu"] = cpu_filter
    if cpu_vendor_filter:
        params["cpu_vendor"] = cpu_vendor_filter
    if agent_filter:
        params["agent"] = agent_filter
    if fresh:
        params["fresh"] = fresh
    if model_filter:
        params["model"] = model_filter
    if chassis_filter:
        params["chassis"] = chassis_filter
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    if page > 1:
        params["page"] = str(page)
    return urlencode(params)



def _devices_filter_chips(
    *,
    tag_filter: Optional[str],
    query: Optional[str],
    show_archive: bool,
    wave_filter: Optional[str],
    os_filter: Optional[str],
    ram_filter: Optional[str],
    disk_filter: Optional[str],
    cpu_filter: Optional[str],
    cpu_vendor_filter: Optional[str],
    agent_filter: Optional[str],
    fresh: Optional[str],
    model_filter: Optional[str] = None,
    chassis_filter: Optional[str] = None,
) -> list[dict[str, str]]:
    chips: list[dict[str, str]] = []
    chassis_label = {
        "laptop": "Ноутбуки",
        "desktop": "Десктоп",
        "server": "Серверы",
        "vm": "ВМ",
        "other": "Другое",
    }.get(chassis_filter or "", chassis_filter or "")
    specs: list[tuple[str, Optional[str], str]] = [
        ("tag", tag_filter, tag_filter or ""),
        ("q", query, query or ""),
        ("wave", wave_filter, wave_filter or ""),
        ("os", os_filter, os_filter or ""),
        ("ram", ram_filter, ram_filter or ""),
        ("disk", disk_filter, disk_filter or ""),
        ("cpu", cpu_filter, cpu_filter or ""),
        ("cpu_vendor", cpu_vendor_filter, cpu_vendor_filter or ""),
        ("agent", agent_filter, f"bAD {agent_filter}" if agent_filter else ""),
        ("fresh", fresh, "Онлайн" if fresh == "ok" else (fresh or "")),
        ("model", model_filter, model_filter or ""),
        ("chassis", chassis_filter, chassis_label),
    ]
    if show_archive:
        specs.append(("archive", "1", "Архив"))

    def _qs(**overrides: Any) -> str:
        base: dict[str, Any] = {
            "tag": tag_filter,
            "q": query,
            "archive": show_archive,
            "page": 1,
            "wave": wave_filter,
            "os_filter": os_filter,
            "ram_filter": ram_filter,
            "disk_filter": disk_filter,
            "cpu_filter": cpu_filter,
            "cpu_vendor_filter": cpu_vendor_filter,
            "agent_filter": agent_filter,
            "fresh": fresh,
            "model_filter": model_filter,
            "chassis_filter": chassis_filter,
        }
        base.update(overrides)
        return _devices_query_params(
            tag=base["tag"],
            q=base["q"],
            archive=bool(base["archive"]),
            page=1,
            wave=base["wave"],
            os_filter=base["os_filter"],
            ram_filter=base["ram_filter"],
            disk_filter=base["disk_filter"],
            cpu_filter=base["cpu_filter"],
            cpu_vendor_filter=base["cpu_vendor_filter"],
            agent_filter=base["agent_filter"],
            fresh=base["fresh"],
            model_filter=base["model_filter"],
            chassis_filter=base["chassis_filter"],
        )

    for param, value, label in specs:
        if not value:
            continue
        if param == "archive":
            without = _qs(archive=False)
        else:
            key = {
                "tag": "tag",
                "q": "q",
                "wave": "wave",
                "os": "os_filter",
                "ram": "ram_filter",
                "disk": "disk_filter",
                "cpu": "cpu_filter",
                "cpu_vendor": "cpu_vendor_filter",
                "agent": "agent_filter",
                "fresh": "fresh",
                "model": "model_filter",
                "chassis": "chassis_filter",
            }[param]
            without = _qs(**{key: None})
        href = f"/devices?{without}" if without else "/devices"
        chips.append({"param": param, "label": label, "href": href})
    return chips



def _attach_duplicate_signals(
    devices: list[dict],
    device_signals: dict[str, dict[str, Any]],
) -> None:
    """Пометить строки списка: is_duplicate + kinds (без merge)."""
    for d in devices:
        sig = device_signals.get(d["bad_id"]) or {}
        d["dup_kinds"] = list(sig.get("kinds") or [])
        d["is_duplicate"] = bool(sig.get("is_duplicate"))
        d["has_agent_local"] = device_has_agent_local(d)



def _inventory_bad_ids(db: Database) -> set[str]:
    """Устройства, у которых сервер уже принял снимок."""
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT bad_id FROM inventory_snapshots"
        ).fetchall()
    return {str(row["bad_id"]) for row in rows if row and row.get("bad_id")}



def _contact_is_after_enroll(device: dict) -> bool:
    seen = parse_utc(device.get("last_seen_at"))
    enrolled = parse_utc(device.get("enrolled_at"))
    return bool(seen is not None and enrolled is not None and seen > enrolled)



def _auth_is_api(device: dict, snapshot_ids: set[str]) -> bool:
    """Снимок или контакт позже регистрации — связь уже с ключом устройства."""
    if str(device.get("bad_id") or "") in snapshot_ids:
        return True
    return _contact_is_after_enroll(device)



_DEVICE_SORTS = {"state", "host", "user", "model", "cpu", "ram", "disk", "os", "ip", "seen"}

_STATE_RANK = {"online": 0, "recent": 1, "stale": 2, "unknown": 3}



def _devices_sort_pair(sort: Optional[str], order: Optional[str]) -> tuple[str, str]:
    key = (sort or "").strip()
    direction = (order or "").strip()
    if key not in _DEVICE_SORTS or direction not in {"asc", "desc"}:
        return "", ""
    return key, direction



def _sort_text(value: object) -> Optional[str]:
    text = str(value or "").strip()
    if not text or text == "—":
        return None
    return text.casefold()



def _ip_octets(value: object) -> Optional[tuple[int, int, int, int]]:
    parts = str(value or "").strip().split(".")
    if len(parts) != 4:
        return None
    try:
        nums = tuple(int(part) for part in parts)
    except ValueError:
        return None
    if any(num < 0 or num > 255 for num in nums):
        return None
    return nums  # type: ignore[return-value]



def _device_sort_value(device: dict, sort: str) -> object:
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    if sort == "state":
        return _STATE_RANK.get(str(device.get("freshness") or "unknown"), 3)
    if sort == "host":
        return _sort_text(device.get("hostname"))
    if sort == "user":
        return _sort_text(device.get("user_display_name"))
    if sort == "model":
        return _sort_text(meta.get("hardware_model"))
    if sort == "cpu":
        return _sort_text(device.get("cpu_display"))
    if sort == "os":
        return _sort_text(device.get("os_display"))
    if sort == "ram":
        try:
            return int(meta.get("ram_bytes"))
        except (TypeError, ValueError):
            return None
    if sort == "disk":
        size = disk_bucket_bytes(meta.get("disk_bucket"))
        return size if size > 0 else None
    if sort == "ip":
        ips = device.get("ip_addresses") or []
        return _ip_octets(ips[0] if ips else "")
    if sort == "seen":
        return parse_utc(device.get("last_seen_at"))
    return None



def _sort_device_rows(rows: list[dict], sort: str, order: str) -> list[dict]:
    if sort not in _DEVICE_SORTS or order not in {"asc", "desc"}:
        return rows
    present: list[tuple[object, dict]] = []
    blank: list[dict] = []
    for row in rows:
        value = _device_sort_value(row, sort)
        if value is None:
            blank.append(row)
        else:
            present.append((value, row))
    present.sort(key=lambda item: item[0], reverse=order == "desc")
    return [row for _value, row in present] + blank



def _devices_wave_context(
    db: Database,
    settings: Settings,
    *,
    tag_filter: Optional[str],
    query: Optional[str],
    show_archive: bool,
    wave: Optional[str],
    page_i: int,
    os_filter: Optional[str] = None,
    ram_filter: Optional[str] = None,
    disk_filter: Optional[str] = None,
    cpu_filter: Optional[str] = None,
    cpu_vendor_filter: Optional[str] = None,
    agent_filter: Optional[str] = None,
    fresh: Optional[str] = None,
    model_filter: Optional[str] = None,
    chassis_filter: Optional[str] = None,
    auth: Optional[str] = None,
    snapshot_ids: Optional[set[str]] = None,
    hide_ids: Optional[set[str]] = None,
    sort: str = "",
    order: str = "",
) -> tuple[list[dict], int, int, int]:
    # Индекс дублей всегда по всему парку (meta), иначе поиск/тег ломают бейджи.
    fleet = db.list_devices(archived=None)
    dup_index = db.duplicate_signal_index(devices=fleet, meta_only=True)
    device_signals = dup_index.get("device_signals") or {}

    drift_ids: set[str] = set()
    stale_sec, recent_sec = _freshness_limits(db, settings)
    if wave == "drift":
        _active, _archived, _stats, ops = _fleet_snapshot(db, settings)
        drift_ids = set(ops.get("version_drift_ids") or [])

    # Фильтр списка без второго SELECT: тот же fleet.
    known_snapshots = snapshot_ids if snapshot_ids is not None else _inventory_bad_ids(db)
    auth_filter = (auth or "").strip()
    if auth_filter != "api":
        auth_filter = ""
    wanted_tag = (tag_filter or "").strip().casefold() or None
    query_cf = (query or "").strip().casefold() or None
    raw: list[dict] = []
    for d in fleet:
        if hide_ids and str(d.get("bad_id") or "") in hide_ids:
            continue
        is_archived = bool(d.get("archived"))
        if show_archive:
            if not is_archived:
                continue
        elif is_archived:
            continue
        d["auth_api"] = _auth_is_api(d, known_snapshots)
        if auth_filter == "api" and not d["auth_api"]:
            continue
        if wanted_tag:
            tags = {str(t).casefold() for t in (d.get("tags") or [])}
            if wanted_tag not in tags:
                continue
        if query_cf:
            hay = f"{d.get('bad_id') or ''} {d.get('hostname') or ''}".casefold()
            if query_cf not in hay:
                meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
                if query_cf not in meta_search_haystack(meta):
                    continue
        raw.append(d)

    enriched = [
        _enrich_device_row(
            d,
            stale_after_seconds=stale_sec,
            recent_after_seconds=recent_sec,
        )
        for d in raw
    ]
    _attach_duplicate_signals(enriched, device_signals)
    filtered = filter_devices_by_wave(
        enriched,
        wave,
        drift_ids=drift_ids,
        stale_after_seconds=stale_sec,
    )
    fresh_ok = (fresh or "").strip().casefold() == "ok"
    facet_active = any(
        (
            os_filter,
            ram_filter,
            disk_filter,
            cpu_filter,
            cpu_vendor_filter,
            agent_filter,
            model_filter,
            chassis_filter,
            fresh_ok,
        )
    )
    if facet_active:
        narrowed = []
        for d in filtered:
            meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
            silence = d.get("silence") or device_silence_status(
                d.get("last_seen_at"), stale_after_seconds=stale_sec
            )
            if meta_facet_matches(
                meta,
                d,
                os_filter=os_filter,
                ram_filter=ram_filter,
                disk_filter=disk_filter,
                cpu_filter=cpu_filter,
                cpu_vendor_filter=cpu_vendor_filter,
                agent_filter=agent_filter,
                model_filter=model_filter,
                chassis_filter=chassis_filter,
                fresh_ok=fresh_ok,
                silence_status=str(silence.get("status") or ""),
            ):
                narrowed.append(d)
        filtered = narrowed
    filtered = _sort_device_rows(filtered, sort, order)
    total = len(filtered)
    page_size = DEVICES_PAGE_SIZE
    pages = max(1, (total + page_size - 1) // page_size) if total else 1
    if page_i > pages:
        page_i = pages
    offset = (page_i - 1) * page_size
    return filtered[offset : offset + page_size], total, pages, page_i



@router.get("/devices", response_class=HTMLResponse)
def devices_page(
    request: Request,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    archive: Optional[str] = None,
    wave: Optional[str] = None,
    os: Optional[str] = None,
    ram: Optional[str] = None,
    disk: Optional[str] = None,
    cpu: Optional[str] = None,
    cpu_vendor: Optional[str] = None,
    agent: Optional[str] = None,
    fresh: Optional[str] = None,
    model: Optional[str] = None,
    chassis: Optional[str] = None,
    auth: Optional[str] = None,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 1,
    flash: Optional[str] = None,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    tag_filter = (tag or "").strip() or None
    query = (q or "").strip() or None
    show_archive = (archive or "").strip() in {"1", "true", "yes"}
    wave_filter = normalize_wave_filter(wave)
    os_filter = (os or "").strip() or None
    ram_filter = (ram or "").strip() or None
    disk_filter = (disk or "").strip() or None
    cpu_filter = (cpu or "").strip() or None
    cpu_vendor_filter = (cpu_vendor or "").strip() or None
    agent_filter = (agent or "").strip() or None
    fresh_filter = (fresh or "").strip() or None
    model_filter = (model or "").strip() or None
    chassis_filter = (chassis or "").strip().casefold() or None
    if chassis_filter and chassis_filter not in {"laptop", "desktop", "server", "vm", "other"}:
        chassis_filter = None
    auth_filter = (auth or "").strip()
    if auth_filter != "api":
        auth_filter = ""
    page_i = max(1, int(page or 1))
    sort_key, order_key = _devices_sort_pair(sort, order)
    snapshot_ids = _inventory_bad_ids(db)
    hidden = {str(item) for item in db.approved_enrollment_bad_ids() if item}
    devices, total, pages, page_i = _devices_wave_context(
        db,
        settings,
        tag_filter=tag_filter,
        query=query,
        show_archive=show_archive,
        wave=wave_filter,
        page_i=page_i,
        os_filter=os_filter,
        ram_filter=ram_filter,
        disk_filter=disk_filter,
        cpu_filter=cpu_filter,
        cpu_vendor_filter=cpu_vendor_filter,
        agent_filter=agent_filter,
        fresh=fresh_filter,
        model_filter=model_filter,
        chassis_filter=chassis_filter,
        auth=auth_filter,
        snapshot_ids=snapshot_ids,
        hide_ids=hidden,
        sort=sort_key,
        order=order_key,
    )

    agent_update = db.get_agent_update()
    qs = _devices_query_params(
        tag=tag_filter,
        q=query,
        archive=show_archive,
        page=page_i,
        wave=wave_filter,
        os_filter=os_filter,
        ram_filter=ram_filter,
        disk_filter=disk_filter,
        cpu_filter=cpu_filter,
        cpu_vendor_filter=cpu_vendor_filter,
        agent_filter=agent_filter,
        fresh=fresh_filter,
        model_filter=model_filter,
        chassis_filter=chassis_filter,
        sort=sort_key,
        order=order_key,
    )
    filter_chips = _devices_filter_chips(
        tag_filter=tag_filter,
        query=query,
        show_archive=show_archive,
        wave_filter=wave_filter,
        os_filter=os_filter,
        ram_filter=ram_filter,
        disk_filter=disk_filter,
        cpu_filter=cpu_filter,
        cpu_vendor_filter=cpu_vendor_filter,
        agent_filter=agent_filter,
        fresh=fresh_filter,
        model_filter=model_filter,
        chassis_filter=chassis_filter,
    )
    flashed = _take_flash(request)
    flash_msg = str(flashed.get("message") or "").strip()
    if flash_msg and len(flash_msg) > 200:
        flash_msg = flash_msg[:200]
    pending_enrollment = (
        db.list_pending_enrollment_requests() if user.is_admin else []
    )
    active_fleet, _archived, fleet_stats, fleet_ops = _fleet_snapshot(db, settings)
    if hidden:
        active_fleet = [
            d for d in active_fleet if str(d.get("bad_id") or "") not in hidden
        ]
        _archived = [
            d for d in _archived if str(d.get("bad_id") or "") not in hidden
        ]
        fleet_stats = db.overview_stats(
            stale_after_seconds=effective_stale_after_seconds(db, settings),
            active=active_fleet,
            archived=_archived,
        )
    auth_api_count = sum(1 for d in active_fleet if _auth_is_api(d, snapshot_ids))
    dashboard = build_dashboard_stats(
        db,
        stale_after_seconds=effective_stale_after_seconds(db, settings),
        stats=fleet_stats,
        active=active_fleet,
        ops=fleet_ops,
    )
    catalog_filter_options = _devices_catalog_filter_options(
        active_fleet, dashboard, fleet_stats
    )
    return _html(
        request,
        "devices.html",
        {
            "devices": devices,
            "user": user,
            "fleet_stats": fleet_stats,
            "agent_update": agent_update,
            "github_repo": settings.github_repo,
            "tag_filter": tag_filter or "",
            "q": query or "",
            "show_archive": show_archive,
            "auth": auth_filter,
            "auth_api_count": auth_api_count,
            "wave": wave_filter or "",
            "os_filter": os_filter or "",
            "ram_filter": ram_filter or "",
            "disk_filter": disk_filter or "",
            "cpu_filter": cpu_filter or "",
            "cpu_vendor_filter": cpu_vendor_filter or "",
            "agent_filter": agent_filter or "",
            "fresh_filter": fresh_filter or "",
            "model_filter": model_filter or "",
            "chassis_filter": chassis_filter or "",
            "sort": sort_key,
            "order": order_key,
            "all_tags": db.list_all_tags(),
            "stale_after_seconds": effective_stale_after_seconds(db, settings),
            "page": page_i,
            "pages": pages,
            "total": total,
            "page_size": DEVICES_PAGE_SIZE,
            "export_qs": qs,
            "flash": flash_msg,
            "enrollment_count": len(pending_enrollment),
            "filter_chips": filter_chips,
            "park_empty": total == 0
            and not (
                tag_filter
                or query
                or wave_filter
                or show_archive
                or auth_filter
                or os_filter
                or ram_filter
                or disk_filter
                or cpu_filter
                or cpu_vendor_filter
                or agent_filter
                or fresh_filter
                or model_filter
                or chassis_filter
            ),
            "filters_active": bool(filter_chips),
            "catalog_filter_options": catalog_filter_options,
            "chassis_labels": _CHASSIS_LABELS_RU,
        },
    )



def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and (mod100 < 10 or mod100 >= 20):
        return few
    return many



def _contact_caption(last_seen_at: object) -> str:
    """Та же относительная подпись, что local-time.js пишет в колонку «Контакт»."""
    seen = parse_utc(str(last_seen_at) if last_seen_at else None)
    if seen is None:
        return ""
    diff = (datetime.now(timezone.utc) - seen).total_seconds()
    if diff < 0:
        diff = 0
    sec = int(diff)
    if sec < 60:
        return "только что"
    minutes = sec // 60
    if minutes < 60:
        return f"{minutes} {_plural_ru(minutes, 'минуту', 'минуты', 'минут')} назад"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} {_plural_ru(hours, 'час', 'часа', 'часов')} назад"
    days = hours // 24
    if days == 1:
        return "день назад"
    if days < 7:
        return f"{days} {_plural_ru(days, 'день', 'дня', 'дней')} назад"
    if days < 14:
        return "неделю назад"
    if days < 30:
        weeks = days // 7
        if weeks < 2:
            return "неделю назад"
        return f"{weeks} {_plural_ru(weeks, 'неделю', 'недели', 'недель')} назад"
    if days < 60:
        return "месяц назад"
    if days < 365:
        months = days // 30
        if months < 2:
            return "месяц назад"
        return f"{months} {_plural_ru(months, 'месяц', 'месяца', 'месяцев')} назад"
    years = days // 365
    if years < 2:
        return "год назад"
    return f"{years} {_plural_ru(years, 'год', 'года', 'лет')} назад"



def _live_text(value: object) -> str:
    text = str(value or "").strip()
    if text == "—":
        return ""
    return text



def _live_device_row(device: dict) -> dict[str, str]:
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    did = str(device.get("bad_id") or "")
    ips = device.get("ip_addresses") or []
    return {
        "bad_id": did,
        "href": str(device.get("device_href") or f"/devices/{did}"),
        "hostname": str(device.get("hostname") or ""),
        "state": str(device.get("freshness") or ""),
        "user": _live_text(device.get("user_display_name")),
        "model": _live_text(meta.get("hardware_model")),
        "cpu": _live_text(device.get("cpu_display")),
        "ram": _live_text(device.get("ram_display")),
        "disk": _live_text(device.get("disk_display")),
        "os": _live_text(device.get("os_display")),
        "ip": _live_text(ips[0] if ips else ""),
        "seen": _contact_caption(device.get("last_seen_at")),
        "seen_at": str(device.get("last_seen_at") or ""),
    }



@router.get("/devices/live.json")
def devices_live_json(
    tag: Optional[str] = None,
    q: Optional[str] = None,
    archive: Optional[str] = None,
    wave: Optional[str] = None,
    os: Optional[str] = None,
    ram: Optional[str] = None,
    disk: Optional[str] = None,
    cpu: Optional[str] = None,
    cpu_vendor: Optional[str] = None,
    agent: Optional[str] = None,
    fresh: Optional[str] = None,
    model: Optional[str] = None,
    chassis: Optional[str] = None,
    auth: Optional[str] = None,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 1,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    del user
    tag_filter = (tag or "").strip() or None
    query = (q or "").strip() or None
    show_archive = (archive or "").strip() in {"1", "true", "yes"}
    wave_filter = normalize_wave_filter(wave)
    os_filter = (os or "").strip() or None
    ram_filter = (ram or "").strip() or None
    disk_filter = (disk or "").strip() or None
    cpu_filter = (cpu or "").strip() or None
    cpu_vendor_filter = (cpu_vendor or "").strip() or None
    agent_filter = (agent or "").strip() or None
    fresh_filter = (fresh or "").strip() or None
    model_filter = (model or "").strip() or None
    chassis_filter = (chassis or "").strip().casefold() or None
    if chassis_filter and chassis_filter not in {"laptop", "desktop", "server", "vm", "other"}:
        chassis_filter = None
    auth_filter = (auth or "").strip()
    if auth_filter != "api":
        auth_filter = ""
    page_i = max(1, int(page or 1))
    sort_key, order_key = _devices_sort_pair(sort, order)
    devices, total, _pages, _page_i = _devices_wave_context(
        db,
        settings,
        tag_filter=tag_filter,
        query=query,
        show_archive=show_archive,
        wave=wave_filter,
        page_i=page_i,
        os_filter=os_filter,
        ram_filter=ram_filter,
        disk_filter=disk_filter,
        cpu_filter=cpu_filter,
        cpu_vendor_filter=cpu_vendor_filter,
        agent_filter=agent_filter,
        fresh=fresh_filter,
        model_filter=model_filter,
        chassis_filter=chassis_filter,
        auth=auth_filter,
        snapshot_ids=_inventory_bad_ids(db),
        hide_ids={str(item) for item in db.approved_enrollment_bad_ids() if item},
        sort=sort_key,
        order=order_key,
    )
    return JSONResponse(
        {"total": total, "devices": [_live_device_row(device) for device in devices]}
    )



_LINK_BLOCK = 4194304



def _stamp_older_than(stamp: object, seconds: int) -> bool:
    text = str(stamp or "").strip()
    if not text:
        return True
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return True
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - moment).total_seconds() > seconds



def _pending_enrollment_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        stale = _stamp_older_than(row.get("seen_at"), 360)
        out.append(
            {
                "id": row.get("id"),
                "hostname": row.get("hostname"),
                "ip": row.get("ip"),
                "serial": row.get("serial"),
                "status_text": "нет связи" if stale else "Ожидает разрешения",
            }
        )
    return out



def _current_arc_size(db: Database) -> int:
    current = db.get_agent_update() or {}
    path = Path(str(current.get("file_path") or ""))
    try:
        if path.is_file():
            return path.stat().st_size
    except OSError:
        return 0
    return 0



def _approved_enrollment_rows(
    db: Database, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    disk: Optional[int] = None
    out: list[dict[str, Any]] = []
    for row in rows:
        total = int(row.get("archive_total") or 0)
        if total <= 0:
            if disk is None:
                disk = _current_arc_size(db)
            total = disk
        received = int(row.get("archive_received") or 0)
        count = (total + _LINK_BLOCK - 1) // _LINK_BLOCK if total > 0 else 0
        state = str(row.get("link_state") or "")
        fresh = not _stamp_older_than(row.get("link_at"), 360)
        downloading = state == "download" and fresh
        complete = total > 0 and received >= total
        cubes: list[str] = []
        marked = False
        for index in range(count):
            last = index + 1 == count
            if received >= (index + 1) * _LINK_BLOCK or (complete and last):
                cubes.append("done")
            elif downloading and not marked:
                cubes.append("download")
                marked = True
            else:
                cubes.append("wait")
        if state == "error":
            status_text = str(row.get("link_error") or "")
            status_kind = "error"
        elif not fresh:
            status_text = "нет связи"
            status_kind = ""
        else:
            status_text = ""
            status_kind = ""
        out.append(
            {
                "id": row.get("id"),
                "hostname": row.get("hostname"),
                "ip": row.get("ip"),
                "cubes": cubes,
                "status_text": status_text,
                "status_kind": status_kind,
            }
        )
    return out



@router.get("/devices/enrollment-requests", response_class=HTMLResponse)
def enrollment_requests_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    flashed = _take_flash(request)
    message = str(flashed.get("message") or "").strip()
    return _html(
        request,
        "enrollment_requests.html",
        {
            "user": user,
            "pending_rows": _pending_enrollment_rows(db.list_pending_enrollment_requests()),
            "approved_rows": _approved_enrollment_rows(
                db, db.list_approved_enrollment_requests()
            ),
            "flash": message[:200] if message else "",
        },
    )



@router.post("/devices/enrollment-requests/{request_id}/allow")
def devices_allow_enrollment_request(
    request_id: str,
    request: Request,
    _user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    page = "/devices/enrollment-requests"
    row = db.get_enrollment_request(request_id)
    if not row or row["status"] != "pending":
        return _see_other(request, page, message="Заявка уже не ждёт разрешения.")
    from .bad_id import (
        bad_id_from_board,
        ensure_bad_id_key,
        is_bad_id,
        normalize_machine_guid,
        random_bad_id,
    )

    presented = str(row.get("bad_id") or "")
    if is_bad_id(presented):
        bad_id = presented.strip()
    else:
        guid = normalize_machine_guid(str(row.get("machine_guid") or ""))
        uuid_value = db.normalize_smbios_uuid(row.get("smbios_uuid")) or ""
        if guid and uuid_value:
            bad_id = bad_id_from_board(guid, uuid_value, ensure_bad_id_key(db))
        else:
            bad_id = ""
            for _ in range(5):
                candidate = random_bad_id()
                if not db.get_device_auth_row(candidate):
                    bad_id = candidate
                    break
            if not bad_id:
                return _see_other(request, page, message="Не удалось выпустить ключ.")
    existing = db.get_device_auth_row(bad_id)
    if existing and existing.get("revoked"):
        return _see_other(
            request, page, message="Карточка отозвана. Кнопка её не возвращает."
        )
    api_key = generate_token("bad_ak_")
    private, public, fingerprint = new_device_signing_key()
    data_key = getattr(request.app.state, "data_key", "") or ""
    lookup = api_key_lookup(data_key, api_key) if data_key else None
    try:
        db.upsert_device_on_enroll(
            bad_id=bad_id,
            hostname=row.get("hostname"),
            api_key_hash=hash_secret(api_key),
            agent_version=None,
            api_key_lookup=lookup,
            allow_existing=existing is not None,
            signing_pubkey=public,
            signing_key_fingerprint=fingerprint,
        )
    except ValueError:
        return _see_other(request, page, message="Не удалось выпустить ключ.")
    latest_archive = db.get_agent_update() or {}
    if not db.mark_enrollment_request_approved(
        request_id,
        bad_id,
        encrypt_secret(data_key, api_key),
        encrypt_secret(data_key, private),
        str(latest_archive.get("archive_password_enc") or ""),
    ):
        return _see_other(request, page, message="Заявка уже не ждёт разрешения.")
    return _see_other(
        request,
        page,
        message="Разрешено. Агент заберёт ключ при следующем подключении.",
    )



@router.get("/devices/export.csv")
def devices_csv_export(
    tag: Optional[str] = None,
    q: Optional[str] = None,
    archive: Optional[str] = None,
    wave: Optional[str] = None,
    _user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    tag_filter = (tag or "").strip() or None
    query = (q or "").strip() or None
    show_archive = (archive or "").strip() in {"1", "true", "yes"}
    wave_filter = normalize_wave_filter(wave)
    rows = db.devices_for_csv(
        tag=tag_filter, archived=show_archive, q=query
    )
    if wave_filter:
        drift_ids: set[str] = set()
        if wave_filter == "drift":
            ops = ops_update_signals(
                db, stale_after_seconds=effective_stale_after_seconds(db, settings)
            )
            drift_ids = {d["bad_id"] for d in (ops.get("version_drift") or [])}
        by_id = {
            d["bad_id"]: d
            for d in db.list_devices(
                tag=tag_filter, archived=show_archive, q=query
            )
        }
        as_devices = [
            by_id[r["bad_id"]] for r in rows if r.get("bad_id") in by_id
        ]
        if wave_filter == "dup":
            # Индекс по всему парку — иначе wave=dup режет «сирот» без пары в выборке.
            signals = (
                db.duplicate_signal_index(
                    devices=db.list_devices(archived=None), meta_only=True
                ).get("device_signals")
                or {}
            )
            _attach_duplicate_signals(as_devices, signals)
        filtered = filter_devices_by_wave(
            as_devices,
            wave_filter,
            drift_ids=drift_ids,
            stale_after_seconds=effective_stale_after_seconds(db, settings),
        )
        kept_ids = {d["bad_id"] for d in filtered}
        rows = [r for r in rows if r.get("bad_id") in kept_ids]
    buf = io.StringIO()
    fields = [
        "bad_id",
        "hostname",
        "tags",
        "agent_version",
        "last_seen_at",
        "enrolled_at",
        "archived",
        "revoked",
        "serial_number",
        "model",
        "manufacturer",
        "cpu",
        "ram_bytes",
        "domain",
        "os",
        "bad_id",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    data = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="bad-devices.csv"',
        },
    )



# Подписи бакетов find_duplicate_devices — одна таблица для warn-box и merge-кнопок.
_DUP_BUCKET_LABELS: tuple[tuple[str, str], ...] = (
    ("hostname", "Тот же hostname"),
    ("serial_number", "Тот же serial"),
    ("smbios_uuid", "Тот же SMBIOS UUID"),
    ("bios_serial", "Тот же BIOS serial"),
    ("identifying_number", "Тот же IdentifyingNumber"),
    ("baseboard_serial", "Тот же serial платы"),
    ("disk_serial_number", "Тот же serial диска"),
)



def _duplicate_groups(
    duplicates: Optional[dict],
) -> list[dict]:
    """Непустые бакеты дублей с русской подписью (порядок как в UI)."""
    if not duplicates:
        return []
    groups: list[dict] = []
    for key, label in _DUP_BUCKET_LABELS:
        devices = duplicates.get(key) or []
        if devices:
            groups.append({"key": key, "label": label, "devices": devices})
    return groups



def _apply_inventory_overlay(detail: dict, payload: dict) -> dict:
    """Снимок для отчёта агента: не пишет в БД, только поля карточки."""
    detail = dict(detail)
    detail["latest_inventory"] = {"payload": payload}
    host = payload.get("host") if isinstance(payload.get("host"), dict) else None
    hostname = str((host or {}).get("hostname") or "").strip()
    if hostname:
        detail["hostname"] = hostname
    agent_version = str(payload.get("agent_version") or "").strip()
    if agent_version:
        detail["agent_version"] = agent_version
    meta = dict(detail.get("meta") or {}) if isinstance(detail.get("meta"), dict) else {}
    meta.update(
        inventory_meta_cache(
            host=host,
            hardware=payload.get("hardware") if isinstance(payload.get("hardware"), dict) else None,
            users=payload.get("users") if isinstance(payload.get("users"), dict) else None,
            network=payload.get("network") if isinstance(payload.get("network"), dict) else None,
        )
    )
    detail["meta"] = meta
    return detail



def _device_config_context(
    db: Database,
    bad_id: str,
    *,
    user: WebUser,
    settings: Settings,
    message: Optional[str] = None,
    error: Optional[str] = None,
    active_view: Optional[str] = None,
    inventory_payload: Optional[dict] = None,
    keep_empty_sections: bool = True,
) -> Optional[dict]:
    detail = db.get_device_detail(bad_id)
    if not detail:
        return None
    if inventory_payload is not None:
        detail = _apply_inventory_overlay(detail, inventory_payload)
    effective = db.compute_device_effective_config(bad_id)
    assert effective is not None
    override = effective.get("override") or {}
    override_settings = override.get("settings") if override else {}
    inventory_pretty = None
    hardware_summary = None
    host_info = None
    network_info = None
    users_info = None
    software_info = None
    minidumps_info = None
    security_info = None
    collector_errors = None
    latest = detail.get("latest_inventory")
    if latest and latest.get("payload") is not None:
        payload = latest["payload"]
        inventory_pretty = json.dumps(payload, indent=2, ensure_ascii=False)
        if isinstance(payload, dict):
            hw = payload.get("hardware")
            if isinstance(hw, dict):
                hardware_summary = hw
            h = payload.get("host")
            if isinstance(h, dict):
                host_info = h
            n = payload.get("network")
            if isinstance(n, dict):
                network_info = n
            u = payload.get("users")
            if isinstance(u, dict):
                users_info = u
            s = payload.get("software")
            if isinstance(s, dict):
                software_info = s
            md = payload.get("minidumps")
            if isinstance(md, dict):
                minidumps_info = md
            sec = payload.get("security")
            if isinstance(sec, dict):
                security_info = sec
            errs = payload.get("collector_errors")
            if isinstance(errs, list):
                collector_errors = errs
    stale_sec, recent_sec = _freshness_limits(db, settings)
    silence = device_silence_status(
        detail.get("last_seen_at"),
        stale_after_seconds=stale_sec,
    )
    hw_chassis = (
        hardware_summary.get("chassis_type")
        if isinstance(hardware_summary, dict)
        else None
    )
    chassis_type = _normalize_chassis_type(
        hw_chassis or _chassis_type_from_device(detail)
    )
    freshness = _device_freshness_tier(
        detail.get("last_seen_at"),
        stale_after_seconds=stale_sec,
        recent_after_seconds=recent_sec,
    )
    recent_events = db.list_device_events(
        bad_id=bad_id, limit=20, include_detail=False
    )
    duplicates = db.find_duplicate_devices(bad_id)
    dup_groups = _duplicate_groups(duplicates)
    for g in dup_groups:
        for d in g.get("devices") or []:
            if isinstance(d, dict):
                d["chassis_type"] = _chassis_type_from_device(d)
    device_meta = detail.get("meta") if isinstance(detail.get("meta"), dict) else {}
    inventory_nav = _device_inventory_nav(
        host_info=host_info,
        hardware_summary=hardware_summary,
        network_info=network_info,
        users_info=users_info,
        software_info=software_info,
        minidumps_info=minidumps_info,
        collector_errors=collector_errors,
        security_info=security_info,
        device_meta=device_meta,
        device_baseboard_serial=detail.get("baseboard_serial"),
        keep_empty=keep_empty_sections,
    )
    inventory_ids = {item["id"] for item in inventory_nav}
    view = (active_view or "").strip()
    if view not in DEVICE_FIXED_VIEWS and view not in inventory_ids:
        view = "overview"
    allowed_keys = sorted(ALLOWED_SETTING_KEYS)
    presence = str(device_meta.get("user_presence") or "")
    if presence == "online":
        user_names = normalize_logged_on_list(device_meta.get("logged_on"))
        user_display_name = user_names[0] if user_names else None
        user_presence_caption = "в системе"
    else:
        user_display_name = device_meta.get("last_logged_on") or None
        user_presence_caption = "последний" if user_display_name else ""
    uninstall = uninstall_ui_context(device_meta)
    uninstall_confirm = device_uninstall_confirm_value(detail)
    device_href = f"/devices/{bad_id}"
    return {
        "device": detail,
        "device_href": device_href,
        "inventory_signing": _device_inventory_signing_line(detail),
        "pending_reboot_visible": _pending_reboot_visible(host_info),
        "reboot_reason_labels": _REBOOT_REASON_LABELS_RU,
        "user_display_name": user_display_name,
        "user_presence": presence if user_display_name else "",
        "user_presence_caption": user_presence_caption,
        "uninstall": uninstall,
        "uninstall_confirm": uninstall_confirm,
        "inventory_pretty": inventory_pretty,
        "hardware_summary": hardware_summary,
        "host_info": host_info,
        "network_info": network_info,
        "users_info": users_info,
        "software_info": software_info,
        "minidumps_info": minidumps_info,
        "security_info": security_info,
        "collector_errors": collector_errors,
        "inventory_nav": inventory_nav,
        "keep_empty_sections": keep_empty_sections,
        "active_view": view or "overview",
        "user": user,
        "message": message,
        "error": error,
        "defaults": dict(DEFAULT_AGENT_SETTINGS),
        "effective": effective["settings"],
        "config_version": effective["version"],
        "matched_policies": effective["matched_policies"],
        "override_settings": override_settings or {},
        "has_override": effective["has_override"],
        # Provenance for UI Lead: agent_local ≠ device_override / policy / default.
        "sources": effective.get("sources") or {},
        "agent_local_keys": effective.get("agent_local_keys") or [],
        "has_agent_local": bool(effective.get("has_agent_local")),
        "config_local": effective.get("config_local"),
        "policy_keys": effective.get("policy_keys") or [],
        "override_keys": effective.get("override_keys") or [],
        "match_context": effective.get("context") or {},
        "allowed_setting_keys": allowed_keys,
        "config_winner": build_config_winner(
            effective=effective,
            sources=effective.get("sources") or {},
            agent_local_keys=list(effective.get("agent_local_keys") or []),
            settings_values=effective.get("settings") or {},
            policy_keys=list(effective.get("policy_keys") or []),
            override_keys=list(effective.get("override_keys") or []),
            allowed_setting_keys=allowed_keys,
        ),
        "silence": silence,
        "freshness": freshness,
        "auth_api": bool(detail.get("latest_inventory")) or _contact_is_after_enroll(detail),
        "health_snippet": health_snippet(detail.get("meta")),
        "chassis_type": chassis_type,
        "chassis_label": _format_chassis(chassis_type if chassis_type != "other" else ""),
        "recent_events": recent_events,
        "tags_text": ", ".join(detail.get("tags") or []),
        "duplicates": duplicates,
        "duplicate_groups": dup_groups,
        "new_api_key": None,
        "msi_versions": db.list_agent_msi_versions(),
    }



def _panel_css() -> str:
    global _panel_css_cache
    if _panel_css_cache is None:
        _panel_css_cache = _PANEL_CSS_PATH.read_text(encoding="utf-8")
    return _panel_css_cache



def render_device_report(
    db: Database,
    settings: Settings,
    bad_id: str,
    inventory_payload: dict,
) -> HTMLResponse:
    """Самодостаточный HTML карточки. Снимок не сохраняется."""
    ctx = _device_config_context(
        db,
        bad_id,
        user=WebUser(username="agent", role="operator", source="local"),
        settings=settings,
        inventory_payload=inventory_payload,
        keep_empty_sections=False,
    )
    if ctx is None:
        raise LookupError(bad_id)
    ctx["report_mode"] = True
    ctx["inline_css"] = _panel_css()
    html_doc = templates.get_template("device_detail.html").render(ctx)
    return HTMLResponse(html_doc)



_REFRESH_SENT_MESSAGE = (
    "Запрос отправлен — применится при следующем heartbeat агента "
    "(обычно в пределах интервала heartbeat)"
)

_UNINSTALL_SENT_MESSAGE = (
    "Команда снятия сохранена. Она уйдёт при следующем heartbeat."
)

_UNINSTALL_CANCEL_MESSAGE = "Снятие агента отменено."

_UNINSTALL_CONFIRM_MISMATCH = (
    "Подтверждение не совпало — введите точное имя узла или идентификатор."
)



def _device_inventory_signing_line(device: dict[str, Any]) -> dict[str, str]:
    """Строка доверия подписи инвентаря (devices.signing_key_fingerprint)."""
    fp = str(device.get("signing_key_fingerprint") or "").strip()
    if not fp:
        return {"state": "none", "label": "ключ не выдан"}
    short = fp if len(fp) <= 16 else f"{fp[:16]}…"
    return {"state": "issued", "label": f"ключ · {short}"}



def _missing_device(request: Request, bad_id: str, user: WebUser):
    return _html(
        request,
        "device_missing.html",
        {"bad_id": bad_id, "user": user},
        status_code=404,
    )



def _archive_device(db: Database, bad_id: str, archived: bool):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    detail = db.get_device_detail(canonical) or {}
    panel_ref = f"/devices/{canonical}"
    if not db.set_device_archived(canonical, archived):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(url=f"{panel_ref}?view=admin", status_code=303)



@router.get("/devices/{bad_id}", response_class=HTMLResponse)
def device_detail_page(
    bad_id: str,
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    view: Optional[str] = None,
    refresh_sent: Optional[str] = None,
    uninstall_sent: Optional[str] = None,
    uninstall_cancelled: Optional[str] = None,
    uninstall_error: Optional[str] = None,
    delete_error: Optional[str] = None,
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return _missing_device(request, bad_id, user)
    bad_id = canonical
    flash_message = None
    error = None
    if refresh_sent == "1":
        flash_message = _REFRESH_SENT_MESSAGE
    elif uninstall_sent == "1":
        flash_message = _UNINSTALL_SENT_MESSAGE
    elif uninstall_cancelled == "1":
        flash_message = _UNINSTALL_CANCEL_MESSAGE
    if uninstall_error == "1" or delete_error == "1":
        error = _UNINSTALL_CONFIRM_MISMATCH
    ctx = _device_config_context(
        db,
        bad_id,
        user=user,
        settings=settings,
        message=flash_message,
        error=error,
        active_view=view or ("admin" if uninstall_error == "1" else None),
    )
    if not ctx:
        return _missing_device(request, bad_id, user)
    return _html(request, "device_detail.html", ctx)



@router.post("/devices/{bad_id}/request-refresh")
def device_request_refresh(
    bad_id: str,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    bad_id = canonical
    if not set_device_refresh_request(db, bad_id):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(
        url=f"/devices/{bad_id}?refresh_sent=1",
        status_code=303,
    )



@router.post("/devices/{bad_id}/uninstall")
def device_uninstall_order(
    bad_id: str,
    confirm: str = Form(""),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    bad_id = canonical
    detail = db.get_device_detail(bad_id)
    if not detail:
        return RedirectResponse(url="/devices", status_code=303)
    panel_ref = f"/devices/{bad_id}"
    if not uninstall_confirm_matches(detail, confirm):
        return RedirectResponse(
            url=f"{panel_ref}?view=admin&uninstall_error=1",
            status_code=303,
        )
    ok, reason = request_device_uninstall(db, bad_id)
    if not ok:
        if reason == "revoked":
            return RedirectResponse(
                url=f"{panel_ref}?view=admin",
                status_code=303,
            )
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(
        url=f"{panel_ref}?view=admin&uninstall_sent=1",
        status_code=303,
    )



@router.post("/devices/{bad_id}/uninstall/cancel")
def device_uninstall_cancel(
    bad_id: str,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    bad_id = canonical
    detail = db.get_device_detail(bad_id) or {}
    panel_ref = f"/devices/{bad_id}"
    if not cancel_device_uninstall(db, bad_id):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(
        url=f"{panel_ref}?view=admin&uninstall_cancelled=1",
        status_code=303,
    )



@router.post("/devices/{bad_id}/revoke")
def device_revoke(
    bad_id: str,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return _missing_device(request, bad_id, user)
    bad_id = canonical
    if not db.set_device_revoked(bad_id, True):
        return _missing_device(request, bad_id, user)
    ctx = _device_config_context(
        db,
        bad_id,
        user=user,
        settings=settings,
        message="Доступ отозван: агент не сможет связаться с сервером до повторной регистрации или выпуска нового ключа",
        active_view="admin",
    )
    assert ctx is not None
    return _html(request, "device_detail.html", ctx)



@router.post("/devices/{bad_id}/rotate-key")
def device_rotate_key(
    bad_id: str,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return _missing_device(request, bad_id, user)
    bad_id = canonical
    if not db.get_device_detail(bad_id):
        return _missing_device(request, bad_id, user)
    api_key = generate_token("bad_ak_")
    data_key = getattr(request.app.state, "data_key", "") or ""
    lookup = api_key_lookup(data_key, api_key) if data_key else None
    db.rotate_device_api_key(
        bad_id, hash_secret(api_key), api_key_lookup=lookup
    )
    ctx = _device_config_context(
        db,
        bad_id,
        user=user,
        settings=settings,
        message="Выпущен новый ключ доступа агента. Сохраните его — повторно показать нельзя.",
        active_view="admin",
    )
    assert ctx is not None
    ctx["new_api_key"] = api_key
    return _html(request, "device_detail.html", ctx)



@router.post("/devices/{bad_id}/archive")
def device_archive(
    bad_id: str,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    return _archive_device(db, bad_id, True)



@router.post("/devices/{bad_id}/restore")
def device_restore(
    bad_id: str,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    return _archive_device(db, bad_id, False)



@router.post("/devices/{bad_id}/delete")
def device_delete(
    bad_id: str,
    confirm: str = Form(""),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    bad_id = canonical
    detail = db.get_device_detail(bad_id) or {}
    panel_ref = f"/devices/{bad_id}"
    if (confirm or "").strip() != bad_id:
        return RedirectResponse(
            url=f"{panel_ref}?delete_error=1", status_code=303
        )
    db.delete_device(bad_id)
    return RedirectResponse(url="/devices", status_code=303)



_MERGE_ERROR_RU: dict[str, str] = {
    "merge_same_device": "Нельзя объединить устройство само с собой.",
    "merge_survivor_missing": "Целевое устройство (survivor) не найдено.",
    "merge_donor_missing": "Донор не найден.",
    "merge_no_identity_match": (
        "Для объединения нужен совпавший серийник корпуса, SMBIOS UUID "
        "или два из BIOS / IdentifyingNumber / платы."
    ),
    "merge_donor_not_stale_or_archived": (
        "Донор должен быть stale или в архиве; два свежих online объединять нельзя."
    ),
}



def _device_merge_page(
    request: Request,
    db: Database,
    survivor_id: str,
    *,
    user: WebUser,
    settings: Settings,
    message: Optional[str] = None,
    error: Optional[str] = None,
    merge_result: Optional[dict] = None,
):
    """Карточка survivor после merge (или ошибка); 404 если устройства нет."""
    ctx = _device_config_context(
        db,
        survivor_id,
        user=user,
        settings=settings,
        message=message,
        error=error,
        active_view="admin",
    )
    if not ctx:
        return _missing_device(request, survivor_id, user)
    if merge_result is not None:
        ctx["merge_result"] = merge_result
    return _html(request, "device_detail.html", ctx)



@router.post("/devices/{survivor_id}/merge")
def device_merge(
    survivor_id: str,
    request: Request,
    donor_id: str = Form(""),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Явный admin merge дублей. Не /v1; ключ донора отзывает merge_devices (DB)."""
    survivor_canonical = (survivor_id if db.get_device_auth_row(survivor_id) else None)
    if not survivor_canonical:
        return _missing_device(request, survivor_id, user)
    survivor_id = survivor_canonical
    donor = (donor_id or "").strip()
    donor_resolved = (donor if donor and db.get_device_auth_row(donor) else None)
    if donor and donor_resolved:
        donor = donor_resolved
    if not donor:
        return _device_merge_page(
            request,
            db,
            survivor_id,
            user=user,
            settings=settings,
            error="Укажите donor_id устройства-донора.",
        )

    try:
        result = db.merge_devices(
            survivor_id,
            donor,
            stale_after_seconds=effective_stale_after_seconds(db, settings),
        )
    except ValueError as exc:
        code = str(exc).strip() or "merge_failed"
        return _device_merge_page(
            request,
            db,
            survivor_id,
            user=user,
            settings=settings,
            error=_MERGE_ERROR_RU.get(
                code, f"Объединение не выполнено ({code})."
            ),
        )

    donor_label = result.get("donor_hostname") or result.get("donor_id") or donor
    matched = ", ".join(result.get("matched") or []) or "—"
    return _device_merge_page(
        request,
        db,
        survivor_id,
        user=user,
        settings=settings,
        message=(
            f"Объединено с «{donor_label}»: история перенесена, донор в архиве"
            f" (совпало: {matched})."
        ),
        merge_result=result,
    )



@router.post("/devices/{bad_id}/tags")
def device_tags_save(
    bad_id: str,
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    tags: str = Form(""),
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return _missing_device(request, bad_id, user)
    bad_id = canonical
    try:
        db.set_device_tags(bad_id, tags)
    except KeyError:
        return _missing_device(request, bad_id, user)
    ctx = _device_config_context(
        db,
        bad_id,
        user=user,
        settings=settings,
        message="Теги сохранены",
        active_view="admin",
    )
    assert ctx is not None
    return _html(request, "device_detail.html", ctx)



@router.post("/devices/{bad_id}/config-override")
def device_config_override_save(
    bad_id: str,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    inventory_interval_hours: str = Form(""),
    heartbeat_interval_minutes: str = Form(""),
    update_check_interval_hours: str = Form(""),
    update_enabled: str = Form(""),
    update_target: str = Form(""),
    collect_hardware: str = Form(""),
    collect_users: str = Form(""),
    collect_software: str = Form(""),
    clear_override: Optional[str] = Form(None),
):
    canonical = (bad_id if db.get_device_auth_row(bad_id) else None)
    if not canonical:
        return _missing_device(request, bad_id, user)
    bad_id = canonical
    if clear_override is not None:
        if not db.get_device_detail(bad_id):
            return _missing_device(request, bad_id, user)
        db.delete_device_config_override(bad_id)
        ctx = _device_config_context(
            db,
            bad_id,
            user=user,
            settings=settings,
            message="Ручное переопределение очищено",
            active_view="config",
        )
        assert ctx is not None
        return _html(request, "device_detail.html", ctx)

    raw = _settings_raw_from_form(
        inventory_interval_hours=inventory_interval_hours,
        heartbeat_interval_minutes=heartbeat_interval_minutes,
        update_check_interval_hours=update_check_interval_hours,
        update_enabled=update_enabled,
        update_target=update_target,
        collect_hardware=collect_hardware,
        collect_users=collect_users,
        collect_software=collect_software,
    )

    cleaned = sanitize_settings(raw)
    if not cleaned:
        ctx = _device_config_context(
            db,
            bad_id,
            user=user,
            settings=settings,
            error="Укажите хотя бы одно поле ручной настройки (или очистите)",
            active_view="config",
        )
        if not ctx:
            return _missing_device(request, bad_id, user)
        return _html(
            request, "device_detail.html", ctx, status_code=400
        )
    pin_err = _validate_update_target_pin(db, cleaned)
    if pin_err:
        ctx = _device_config_context(
            db,
            bad_id,
            user=user,
            settings=settings,
            error=pin_err,
            active_view="config",
        )
        assert ctx is not None
        return _html(request, "device_detail.html", ctx, status_code=400)
    try:
        db.set_device_config_override(bad_id, cleaned)
    except KeyError:
        return _missing_device(request, bad_id, user)
    ctx = _device_config_context(
        db,
        bad_id,
        user=user,
        settings=settings,
        message="Ручное переопределение сохранено",
        active_view="config",
    )
    assert ctx is not None
    return _html(request, "device_detail.html", ctx)
