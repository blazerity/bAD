from __future__ import annotations

import csv
import io
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from . import __version__
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
    DEVICE_STALE_MAX_SECONDS,
    DEVICE_STALE_MIN_SECONDS,
    DEVICE_STALE_SITE_SECRET_KEY,
    device_silence_status,
    effective_stale_after_seconds,
    health_snippet,
    normalize_tags,
    parse_site_stale_seconds,
    parse_utc,
)
from .ldap_client import settings_from_row, test_connection
from .security import api_key_lookup, generate_token, hash_secret, verify_secret
from .sessions import SESSION_COOKIE, SESSION_MAX_AGE, WebUser, dump_session
from .agent_update import (
    delete_msi_version,
    ingest_uploaded_msi,
    ops_update_signals,
    set_latest_msi_version,
    sync_from_github,
)
from .backup import backup_keys_status, backup_status, run_daily_backup
from .enrollment_ops import (
    enrollment_rotation_signals,
    enrollment_status,
    mark_enrollment_wave_done,
    rotate_enrollment_token,
)
from .http_bootstrap import HTTP_SENSITIVE_MSG, client_ip, sensitive_over_http_blocked
from .qa_ui import panel_tls_mode, patch_security_for_qa
from .device_meta import (
    format_logged_on_display,
    meta_search_haystack,
    normalize_logged_on_list,
    normalize_logged_on_user,
)
from .server_runtime import build_server_runtime
from .panel_search import (
    device_match_label,
    device_search_meta_line,
    event_match_label,
    highlight_match,
    matched_serial_subtitle,
)
from .bad_id import device_panel_href
from .fleet_buckets import disk_role, meta_facet_matches
from .wave_21_migration import resolve_device_ref
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
    wait_for_apply as server_wait_for_apply,
)
from .event_importance import FILTER_PRESET_LABELS_RU, IMPORTANCE_LABELS_RU, event_importance
from .smtp_mail import (
    DEFAULT_NOTIFY,
    NOTIFY_LABELS_RU,
    build_hardware_email,
    default_digest_weekdays,
    digest_schedule_preview_ru,
    dump_notify_flags,
    parse_digest_weekdays,
    parse_notify_flags,
    parse_recipients,
    send_email,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["app_version"] = __version__


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
    last_seen_at: Optional[str], *, stale_after_seconds: int
) -> str:
    """UI: online | recent | stale | unknown (порог stale не меняется)."""
    silence = device_silence_status(
        last_seen_at, stale_after_seconds=stale_after_seconds
    )
    status = silence.get("status") or "unknown"
    if status == "unknown":
        return "unknown"
    if status == "stale":
        return "stale"
    seen = parse_utc(last_seen_at)
    if seen is None:
        return "unknown"
    age = max(0, int((datetime.now(timezone.utc) - seen).total_seconds()))
    threshold = max(1, int(stale_after_seconds))
    online_cap = min(600, max(120, threshold // 3))
    return "online" if age <= online_cap else "recent"


def _search_match_reason(device: dict, query: str) -> str:
    return device_match_label(device, query)


def _chassis_map_for_devices(devices: list[dict]) -> dict[str, str]:
    return {str(d["device_id"]): _chassis_type_from_device(d) for d in devices if d.get("device_id")}


def _format_event_type(value: object, empty: str = "") -> str:
    if value is None:
        return empty
    key = str(value).strip()
    if not key:
        return empty
    return _EVENT_TYPE_LABELS_RU.get(key, key)


templates.env.filters["format_bytes"] = _format_bytes
templates.env.filters["format_os"] = _format_os
templates.env.filters["format_chassis"] = _format_chassis
templates.env.filters["format_event_type"] = _format_event_type


def _importance_label_ru(level: object, empty: str = "") -> str:
    if level is None:
        return empty
    return IMPORTANCE_LABELS_RU.get(str(level), str(level))


templates.env.filters["importance_label_ru"] = _importance_label_ru
templates.env.filters["format_logged_on"] = format_logged_on_display
templates.env.filters["logged_on_names"] = normalize_logged_on_list
templates.env.filters["logged_on_user"] = normalize_logged_on_user

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


templates.env.filters["disk_role_label"] = _disk_role_label_ru


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
    device_id: str = "",
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
) -> str:
    """URL списка с сохранением фильтров (серверная пагинация ?page=)."""
    params: dict[str, str] = {}
    if device_id:
        params["device_id"] = device_id
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


templates.env.filters["pager_items"] = _pager_items
templates.env.filters["pager_url"] = _pager_url
templates.env.globals["event_importance"] = event_importance
templates.env.globals["importance_filter_labels"] = FILTER_PRESET_LABELS_RU
templates.env.globals["event_type_filter_labels"] = _EVENT_TYPE_LABELS_RU

router = APIRouter(tags=["web"], dependencies=[Depends(ensure_csrf)])

DEVICES_PAGE_SIZE = 50
EVENTS_PAGE_SIZE = 50

# Панели карточки: overview/config/admin/events + inventory ids при наличии данных.
DEVICE_FIXED_VIEWS = frozenset({"overview", "config", "admin", "events"})


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

    if host_info:
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

    if hw and hw.get("cpu"):
        cpu = hw["cpu"] if isinstance(hw["cpu"], dict) else {}
        name = str(cpu.get("name") or "").strip() or "CPU"
        cores = cpu.get("cores")
        logical = cpu.get("logical")
        if cores is not None or logical is not None:
            c = cores if cores is not None else "-"
            lg = logical if logical is not None else "-"
            name = f"{name} · {c}/{lg}"
        add("cpu", "cpu", "Процессор", [name])

    if hw and (
        hw.get("manufacturer")
        or hw.get("model")
        or hw.get("serial_number")
        or hw.get("bios_version")
        or hw.get("bios_manufacturer")
        or hw.get("bios_release_date")
        or hw.get("baseboard_serial")
    ):
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

    if hw and (
        hw.get("disks")
        or hw.get("volumes")
        or hw.get("chassis_type")
    ):
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
        else:
            chassis = _format_chassis(hw.get("chassis_type"))
            add(
                "storage",
                "disk",
                "Накопители",
                [f"корпус {chassis}" if chassis else "накопители"],
            )

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

    if hw and hw.get("battery"):
        bat = hw["battery"] if isinstance(hw["battery"], dict) else {}
        charge = bat.get("charge_percent")
        if charge is not None:
            line = f"{charge}%"
            if bat.get("status"):
                line = f"{line} · {bat.get('status')}"
        else:
            line = str(bat.get("status") or "батарея")
        add("battery", "battery", "Батарея", [line])

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

    sec = security_info if isinstance(security_info, dict) else None
    if sec and (
        sec.get("tpm_present") is not None
        or sec.get("secure_boot") is not None
        or sec.get("antivirus")
        or sec.get("tpm_spec_version")
    ):
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

    if collector_errors:
        add("errors", "events", "Ошибки сбора", [f"{len(collector_errors)} ошибок"])

    return items


def _set_session_cookie(
    resp: RedirectResponse,
    secret: str,
    user: WebUser,
    *,
    request: Request,
    settings: Settings,
) -> None:
    secure = cookie_secure_for_request(request, settings.cookie_secure)
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=dump_session(secret, user),
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=SESSION_MAX_AGE,
        path="/",
    )


def _clear_session_cookie(resp: RedirectResponse) -> None:
    resp.delete_cookie(SESSION_COOKIE, path="/")


def _html(
    request: Request,
    name: str,
    context: dict,
    status_code: int = 200,
):
    """TemplateResponse + CSRF token/cookie (SEC-010)."""
    token = get_csrf_token(request)
    ctx = dict(context)
    ctx["csrf_token"] = token
    settings = get_settings()
    ctx["qa_ui"] = settings.qa_ui
    # Global HTTP bootstrap chrome (banner + gated settings actions).
    actual_tls = ctx.get("tls_mode") or tls_panel_mode()
    ctx["tls_mode"] = panel_tls_mode(settings, actual_tls)
    if "tls_domain" not in ctx:
        ctx["tls_domain"] = read_domain_from_env()
    if "https_url" not in ctx:
        ctx["https_url"] = https_panel_url(ctx.get("tls_domain") or "")
    resp = templates.TemplateResponse(request, name, ctx, status_code=status_code)
    set_csrf_cookie(
        resp,
        token,
        secure=cookie_secure_for_request(request, settings.cookie_secure),
    )
    return resp


class LdapFormData:
    """Общие Form-поля для POST save/test LDAP."""

    def __init__(
        self,
        enabled: Optional[str] = Form(None),
        host: str = Form(""),
        port: str = Form("389"),
        use_ssl: Optional[str] = Form(None),
        start_tls: Optional[str] = Form(None),
        bind_dn: str = Form(""),
        bind_password: str = Form(""),
        user_search_base: str = Form(""),
        user_filter_template: str = Form("(uid={username})"),
        display_name_attr: str = Form("cn"),
        default_role: str = Form("operator"),
        allowed_group: str = Form(""),
        tls_insecure: Optional[str] = Form(None),
    ):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.start_tls = start_tls
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.user_search_base = user_search_base
        self.user_filter_template = user_filter_template
        self.display_name_attr = display_name_attr
        self.default_role = default_role
        self.allowed_group = allowed_group
        self.tls_insecure = tls_insecure


class SmtpFormData:
    """Общие Form-поля для POST save/test почты."""

    def __init__(
        self,
        enabled: Optional[str] = Form(None),
        host: str = Form(""),
        port: str = Form("587"),
        use_ssl: Optional[str] = Form(None),
        use_starttls: Optional[str] = Form(None),
        username: str = Form(""),
        password: str = Form(""),
        from_addr: str = Form(""),
        to_addrs: str = Form(""),
        notify_hardware: Optional[str] = Form(None),
        notify_stale: Optional[str] = Form(None),
        notify_enroll: Optional[str] = Form(None),
        notify_hostname: Optional[str] = Form(None),
        notify_domain: Optional[str] = Form(None),
        notify_pending_reboot: Optional[str] = Form(None),
        notify_online: Optional[str] = Form(None),
        notify_disk_space: Optional[str] = Form(None),
        digest_interval_hours: str = Form("3"),
        digest_lookback_hours: str = Form("3"),
        digest_window_start_hour: str = Form("9"),
        digest_window_end_hour: str = Form("19"),
        digest_wd_0: Optional[str] = Form(None),
        digest_wd_1: Optional[str] = Form(None),
        digest_wd_2: Optional[str] = Form(None),
        digest_wd_3: Optional[str] = Form(None),
        digest_wd_4: Optional[str] = Form(None),
        digest_wd_5: Optional[str] = Form(None),
        digest_wd_6: Optional[str] = Form(None),
    ):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.use_starttls = use_starttls
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.notify_hardware = notify_hardware
        self.notify_stale = notify_stale
        self.notify_enroll = notify_enroll
        self.notify_hostname = notify_hostname
        self.notify_domain = notify_domain
        self.notify_pending_reboot = notify_pending_reboot
        self.notify_online = notify_online
        self.notify_disk_space = notify_disk_space
        self.digest_interval_hours = digest_interval_hours
        self.digest_lookback_hours = digest_lookback_hours
        self.digest_window_start_hour = digest_window_start_hour
        self.digest_window_end_hour = digest_window_end_hour
        self.digest_wd_0 = digest_wd_0
        self.digest_wd_1 = digest_wd_1
        self.digest_wd_2 = digest_wd_2
        self.digest_wd_3 = digest_wd_3
        self.digest_wd_4 = digest_wd_4
        self.digest_wd_5 = digest_wd_5
        self.digest_wd_6 = digest_wd_6


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


def _parse_event_ts(raw: object) -> Optional[datetime]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


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
        did = str(ev.get("device_id") or "")
        ts = _parse_event_ts(ev.get("created_at"))
        merged = dict(ev)
        if etype in disk_pair and did and ts is not None:
            partner_idx = None
            want = "disk_added" if etype == "disk_removed" else "disk_removed"
            for j, other in indexed:
                if j <= i or j in used or not isinstance(other, dict):
                    continue
                if str(other.get("device_id") or "") != did:
                    continue
                if str(other.get("type") or "") != want:
                    continue
                ots = _parse_event_ts(other.get("created_at"))
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


def _overview_page_context(
    *,
    user: WebUser,
    db: Database,
    settings: Settings,
) -> dict[str, Any]:
    """SSR context Обзора — Command Center (оперативный пульт)."""
    active, _archived, stats, ops = _fleet_snapshot(db, settings)
    security = patch_security_for_qa(security_status(db, settings), settings)
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
    tls_mode = panel_tls_mode(
        settings, str(ops.get("tls_mode") or tls_panel_mode() or "http")
    )
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
    fleet_by_id = {str(d["device_id"]): d for d in active if d.get("device_id")}
    for d in ops.get("version_drift") or []:
        if isinstance(d, dict):
            d["chassis_type"] = chassis_by_id.get(str(d.get("device_id") or ""), "other")
    raw_feed: list[dict[str, Any]] = []
    for e in stats.get("recent_hardware_events") or []:
        if not isinstance(e, dict):
            continue
        did = str(e.get("device_id") or "")
        e = dict(e)
        e["chassis_type"] = chassis_by_id.get(did, "other")
        dev = fleet_by_id.get(did) or {}
        e["bad_id"] = dev.get("bad_id")
        e["device_href"] = device_panel_href(dev.get("bad_id"), did)
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
            did = str(e.get("device_id") or "")
            e = dict(e)
            e["chassis_type"] = chassis_by_id.get(did, "other")
            dev = fleet_by_id.get(did) or {}
            e["bad_id"] = dev.get("bad_id")
            e["device_href"] = device_panel_href(dev.get("bad_id"), did)
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
        qa_ui=settings.qa_ui,
    )
    server_current = server_read_current(releases_dir(settings))
    events_total = db.count_device_events(importance="all")
    critical_event_count = db.count_device_events(importance="critical")
    high_event_count = db.count_device_events(importance="high")
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


@router.get("/overview/search.json")
def overview_search_json(
    q: str = Query(default="", max_length=128),
    limit: int = Query(default=30, ge=1, le=50),
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    """Глобальный поиск Обзора: устройства + события (сессия)."""
    del user
    query = (q or "").strip()
    if len(query) < 2:
        return JSONResponse({"devices": [], "events": [], "users": []})
    dev_cap = max(1, min(int(limit), 40))
    evt_cap = max(1, min(20, dev_cap))
    devices = db.search_devices_global(query, limit=dev_cap)
    events = db.list_device_events(
        q=query,
        importance="all",
        limit=evt_cap,
        offset=0,
        include_detail=False,
    )
    payloads = db.latest_inventory_payloads(
        [str(d.get("device_id") or "") for d in devices],
        cap=max(len(devices), 1),
    )
    dev_out = []
    for d in devices:
        did = d["device_id"]
        label = d.get("hostname") or did
        hw = None
        payload = payloads.get(str(did))
        if isinstance(payload, dict):
            raw_hw = payload.get("hardware")
            hw = raw_hw if isinstance(raw_hw, dict) else None
        reason = device_match_label(d, query, hardware=hw)
        subtitle = matched_serial_subtitle(d, query, hardware=hw) or reason
        dev_out.append(
            {
                "kind": "device",
                "device_id": did,
                "bad_id": d.get("bad_id"),
                "hostname": label,
                "href": device_panel_href(d.get("bad_id"), did),
                "chassis_type": _chassis_type_from_device(d),
                "match_reason": reason,
                "title_html": highlight_match(label, query),
                "subtitle_html": highlight_match(subtitle, query),
                "archived": bool(d.get("archived")),
            }
        )
    users_out = _overview_search_users(query, db.list_devices(archived=False))
    evt_out = []
    for e in events:
        eid = int(e["id"])
        evt_out.append(
            {
                "kind": "event",
                "id": eid,
                "href": f"/events/{eid}",
                "device_id": e.get("device_id"),
                "hostname": e.get("hostname") or e.get("device_id"),
                "type": e.get("type"),
                "summary": e.get("summary"),
                "match_reason": event_match_label(e, query),
                "title_html": highlight_match(e.get("summary") or "", query),
                "subtitle_html": highlight_match(
                    e.get("hostname") or e.get("device_id") or "", query
                ),
                "created_at": e.get("created_at"),
            }
        )
    return JSONResponse(
        {"devices": dev_out, "events": evt_out, "users": users_out, "q": query}
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Отдельная вкладка Дашборд: конфигурация парка (не /v1)."""
    active, _archived, stats, ops = _fleet_snapshot(db, settings)
    security = patch_security_for_qa(security_status(db, settings), settings)
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


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    user: Optional[WebUser] = Depends(current_web_user),
    db: Database = Depends(get_db),
):
    if user:
        return RedirectResponse(url="/", status_code=303)
    ldap = db.get_ldap_settings()
    return _html(
        request,
        "login.html",
        {
            "error": None,
            "ldap_enabled": bool(ldap.get("enabled")),
            "user": None,
        },
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
    session_secret: str = Depends(get_session_secret),
    settings: Settings = Depends(get_settings),
):
    client = client_ip(request)
    user_key = (username or "").strip().casefold() or "-"
    ip_limiter = getattr(request.app.state, "login_ip_limiter", None)
    user_limiter = getattr(request.app.state, "login_user_limiter", None)
    if ip_limiter is not None and not ip_limiter.allow(client):
        ldap = db.get_ldap_settings()
        return _html(
            request,
            "login.html",
            {
                "error": "Слишком много попыток входа с этого адреса. Подождите минуту.",
                "ldap_enabled": bool(ldap.get("enabled")),
                "user": None,
            },
            status_code=429,
        )
    if user_limiter is not None and not user_limiter.allow(f"u:{user_key}"):
        ldap = db.get_ldap_settings()
        return _html(
            request,
            "login.html",
            {
                "error": "Слишком много попыток для этого имени. Подождите минуту.",
                "ldap_enabled": bool(ldap.get("enabled")),
                "user": None,
            },
            status_code=429,
        )

    user, auth_error = authenticate_web_user(db, data_key, username.strip(), password)
    ldap = db.get_ldap_settings()
    if not user:
        return _html(
            request,
            "login.html",
            {
                "error": auth_error or "Неверное имя пользователя или пароль",
                "ldap_enabled": bool(ldap.get("enabled")),
                "user": None,
            },
            status_code=401,
        )
    dest = "/account/password" if user.must_change_password else "/"
    resp = RedirectResponse(url=dest, status_code=303)
    _set_session_cookie(resp, session_secret, user, request=request, settings=settings)
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    _clear_session_cookie(resp)
    return resp


def _enrich_device_row(device: dict, *, stale_after_seconds: int) -> dict:
    device = dict(device)
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    device["silence"] = device_silence_status(
        device.get("last_seen_at"),
        stale_after_seconds=stale_after_seconds,
    )
    device["chassis_type"] = _chassis_type_from_device(device)
    device["chassis_label"] = _format_chassis(device["chassis_type"])
    device["freshness"] = _device_freshness_tier(
        device.get("last_seen_at"), stale_after_seconds=stale_after_seconds
    )
    device["bad_id"] = device.get("bad_id") or meta.get("bad_id")
    did = str(device.get("device_id") or "")
    device["device_href"] = device_panel_href(device.get("bad_id"), did)
    device["ram_display"] = meta.get("ram_display") or "—"
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
        device["ip_display"] = " · ".join(str(x) for x in ips if x)
        device["ip_copy"] = ", ".join(str(x) for x in ips if x)
        device["ip_title"] = device["ip_display"]
    else:
        device["ip_display"] = "—"
        device["ip_copy"] = ""
        device["ip_title"] = ""
    return device


def _overview_search_users(query: str, fleet: list[dict]) -> list[dict]:
    qcf = (query or "").strip().casefold()
    if len(qcf) < 2:
        return []
    groups: dict[str, dict[str, Any]] = {}
    for d in fleet:
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        did = str(d.get("device_id") or "")
        href = device_panel_href(d.get("bad_id"), did)
        host = d.get("hostname") or did
        entries: list[tuple[str, str]] = []
        logged = normalize_logged_on_list(meta.get("logged_on"))
        if logged:
            for name in logged:
                entries.append((name, "online"))
        else:
            last = meta.get("last_logged_on")
            if last:
                entries.append((str(last), str(meta.get("user_presence") or "last")))
        for name, presence in entries:
            if qcf not in name.casefold():
                continue
            key = name.casefold()
            grp = groups.get(key)
            if not grp:
                grp = {
                    "kind": "user",
                    "name": name,
                    "presence": presence,
                    "devices": [],
                }
                groups[key] = grp
            grp["devices"].append(
                {
                    "hostname": host,
                    "bad_id": d.get("bad_id"),
                    "href": href,
                    "presence": presence,
                }
            )
            if presence == "online":
                grp["presence"] = "online"
    ranked = sorted(groups.values(), key=lambda g: str(g.get("name") or "").casefold())
    return ranked[:15]


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
    for d in fleet:
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        vendor = str(meta.get("cpu_vendor") or "").strip()
        if vendor and _facet_catalog_label_ok(vendor):
            vendor_vals.add(vendor)
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
        "desktop": "ПК",
        "server": "Серверы",
        "vm": "ВМ",
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
        sig = device_signals.get(d["device_id"]) or {}
        d["dup_kinds"] = list(sig.get("kinds") or [])
        d["is_duplicate"] = bool(sig.get("is_duplicate"))
        d["has_agent_local"] = device_has_agent_local(d)


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
) -> tuple[list[dict], int, int, int]:
    # Индекс дублей всегда по всему парку (meta), иначе поиск/тег ломают бейджи.
    fleet = db.list_devices(archived=None)
    dup_index = db.duplicate_signal_index(devices=fleet, meta_only=True)
    device_signals = dup_index.get("device_signals") or {}

    drift_ids: set[str] = set()
    stale_sec = effective_stale_after_seconds(db, settings)
    if wave == "drift":
        _active, _archived, _stats, ops = _fleet_snapshot(db, settings)
        drift_ids = set(ops.get("version_drift_ids") or [])

    # Фильтр списка без второго SELECT: тот же fleet.
    wanted_tag = (tag_filter or "").strip().casefold() or None
    query_cf = (query or "").strip().casefold() or None
    raw: list[dict] = []
    for d in fleet:
        is_archived = bool(d.get("archived"))
        if show_archive:
            if not is_archived:
                continue
        elif is_archived:
            continue
        if wanted_tag:
            tags = {str(t).casefold() for t in (d.get("tags") or [])}
            if wanted_tag not in tags:
                continue
        if query_cf:
            hay = (
                f"{d.get('device_id') or ''} {d.get('hostname') or ''} "
                f"{d.get('bad_id') or ''}"
            ).casefold()
            if query_cf not in hay:
                meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
                if query_cf not in meta_search_haystack(meta):
                    continue
        raw.append(d)

    enriched = [_enrich_device_row(d, stale_after_seconds=stale_sec) for d in raw]
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
    page_i = max(1, int(page or 1))
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
    flash_msg = (flash or "").strip() or None
    if flash_msg and len(flash_msg) > 200:
        flash_msg = flash_msg[:200]
    active_fleet, _archived, fleet_stats, fleet_ops = _fleet_snapshot(db, settings)
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
            "all_tags": db.list_all_tags(),
            "stale_after_seconds": effective_stale_after_seconds(db, settings),
            "page": page_i,
            "pages": pages,
            "total": total,
            "page_size": DEVICES_PAGE_SIZE,
            "export_qs": qs,
            "flash": flash_msg,
            "filter_chips": filter_chips,
            "park_empty": total == 0
            and not (
                tag_filter
                or query
                or wave_filter
                or show_archive
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
        },
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
            drift_ids = {d["device_id"] for d in (ops.get("version_drift") or [])}
        by_id = {
            d["device_id"]: d
            for d in db.list_devices(
                tag=tag_filter, archived=show_archive, q=query
            )
        }
        as_devices = [
            by_id[r["device_id"]] for r in rows if r.get("device_id") in by_id
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
        kept_ids = {d["device_id"] for d in filtered}
        rows = [r for r in rows if r.get("device_id") in kept_ids]
    buf = io.StringIO()
    fields = [
        "device_id",
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
            [str(d.get("device_id") or "") for d in rows],
            cap=max(len(rows), 1),
        )
        if len(query) >= 2
        else {}
    )
    out = []
    for d in rows:
        label = d.get("hostname") or d["device_id"]
        hw = None
        payload = payloads.get(str(d.get("device_id") or ""))
        if isinstance(payload, dict):
            raw_hw = payload.get("hardware")
            hw = raw_hw if isinstance(raw_hw, dict) else None
        reason = device_match_label(d, query, hardware=hw)
        meta_line = matched_serial_subtitle(d, query, hardware=hw) or reason
        out.append(
            {
                "device_id": d["device_id"],
                "hostname": label,
                "href": device_panel_href(d.get("bad_id"), d["device_id"]),
                "chassis_type": _chassis_type_from_device(d),
                "chassis_label": _format_chassis(_chassis_type_from_device(d)),
                "match_reason": reason,
                "title_html": highlight_match(label, query),
                "subtitle_html": highlight_match(meta_line, query),
            }
        )
    return JSONResponse({"devices": out})


@router.get("/setup/progress.json")
def setup_progress_json(
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """U5: явный прогресс мастера (шаг 1/2/3) для UI без своих эвристик."""
    _active, _archived, stats, ops = _fleet_snapshot(db, settings)
    security = patch_security_for_qa(security_status(db, settings), settings)
    ops = merge_security_into_ops(ops, security)
    progress = build_bootstrap_progress(
        user=user,
        ops=ops,
        active_devices=int(stats.get("total_active") or 0),
        security=security,
        settings=settings,
    )
    return JSONResponse({"progress": progress})


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

    device_id = str(event.get("device_id") or "")
    chassis = "other"
    user_display_name = None
    user_presence = ""
    user_presence_caption = ""
    hardware_model = None
    hardware_manufacturer = None
    device_detail = None
    if device_id:
        device_detail = db.get_device_detail(device_id)
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
    device_id: Optional[str] = None,
    q: Optional[str] = None,
    importance: Optional[str] = None,
    type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    device_filter = (device_id or "").strip() or None
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
        "device_id": device_filter,
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
        device_id=device_filter,
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
        e["chassis_type"] = chassis_by_id.get(str(e.get("device_id") or ""), "other")
        e["event_icon"] = event_visual(str(e.get("type") or "")).get("icon") or "events"
    today_d = datetime.now(timezone.utc).date()
    yesterday_d = today_d - timedelta(days=1)
    chip_kw = {
        "device_id": device_filter,
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
            "page_size": page_size,
            "today_utc": today_d.isoformat(),
            "yesterday_utc": yesterday_d.isoformat(),
            "event_filter_counts": event_filter_counts,
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


def _device_config_context(
    db: Database,
    device_id: str,
    *,
    user: WebUser,
    settings: Settings,
    message: Optional[str] = None,
    error: Optional[str] = None,
    active_view: Optional[str] = None,
) -> Optional[dict]:
    detail = db.get_device_detail(device_id)
    if not detail:
        return None
    effective = db.compute_device_effective_config(device_id)
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
    stale_sec = effective_stale_after_seconds(db, settings)
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
        detail.get("last_seen_at"), stale_after_seconds=stale_sec
    )
    recent_events = db.list_device_events(
        device_id=device_id, limit=20, include_detail=False
    )
    duplicates = db.find_duplicate_devices(device_id)
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
    device_href = device_panel_href(detail.get("bad_id"), device_id)
    return {
        "device": detail,
        "device_href": device_href,
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


@router.get("/devices/{device_id}", response_class=HTMLResponse)
def device_detail_page(
    device_id: str,
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
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    device_id = canonical
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
        device_id,
        user=user,
        settings=settings,
        message=flash_message,
        error=error,
        active_view=view or ("admin" if uninstall_error == "1" else None),
    )
    if not ctx:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    return _html(request, "device_detail.html", ctx)


@router.post("/devices/{device_id}/request-refresh")
def device_request_refresh(
    device_id: str,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    device_id = canonical
    if not set_device_refresh_request(db, device_id):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(
        url=f"/devices/{device_id}?refresh_sent=1",
        status_code=303,
    )


@router.post("/devices/{device_id}/uninstall")
def device_uninstall_order(
    device_id: str,
    confirm: str = Form(""),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    device_id = canonical
    detail = db.get_device_detail(device_id)
    if not detail:
        return RedirectResponse(url="/devices", status_code=303)
    panel_ref = device_panel_href(detail.get("bad_id"), device_id)
    if not uninstall_confirm_matches(detail, confirm):
        return RedirectResponse(
            url=f"{panel_ref}?view=admin&uninstall_error=1",
            status_code=303,
        )
    ok, reason = request_device_uninstall(db, device_id)
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


@router.post("/devices/{device_id}/uninstall/cancel")
def device_uninstall_cancel(
    device_id: str,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    device_id = canonical
    detail = db.get_device_detail(device_id) or {}
    panel_ref = device_panel_href(detail.get("bad_id"), device_id)
    if not cancel_device_uninstall(db, device_id):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(
        url=f"{panel_ref}?view=admin&uninstall_cancelled=1",
        status_code=303,
    )


@router.post("/devices/{device_id}/revoke")
def device_revoke(
    device_id: str,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    device_id = canonical
    if not db.set_device_revoked(device_id, True):
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    ctx = _device_config_context(
        db,
        device_id,
        user=user,
        settings=settings,
        message="Доступ отозван: агент не сможет связаться с сервером до повторной регистрации или выпуска нового ключа",
        active_view="admin",
    )
    assert ctx is not None
    return _html(request, "device_detail.html", ctx)


@router.post("/devices/{device_id}/rotate-key")
def device_rotate_key(
    device_id: str,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    device_id = canonical
    if not db.get_device_detail(device_id):
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    api_key = generate_token("bad_ak_")
    data_key = getattr(request.app.state, "data_key", "") or ""
    lookup = api_key_lookup(data_key, api_key) if data_key else None
    db.rotate_device_api_key(
        device_id, hash_secret(api_key), api_key_lookup=lookup
    )
    ctx = _device_config_context(
        db,
        device_id,
        user=user,
        settings=settings,
        message="Выпущен новый ключ доступа агента. Сохраните его — повторно показать нельзя.",
        active_view="admin",
    )
    assert ctx is not None
    ctx["new_api_key"] = api_key
    return _html(request, "device_detail.html", ctx)


@router.post("/devices/{device_id}/archive")
def device_archive(
    device_id: str,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    device_id = canonical
    detail = db.get_device_detail(device_id) or {}
    panel_ref = device_panel_href(detail.get("bad_id"), device_id)
    if not db.set_device_archived(device_id, True):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(url=f"{panel_ref}?view=admin", status_code=303)


@router.post("/devices/{device_id}/restore")
def device_restore(
    device_id: str,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    device_id = canonical
    detail = db.get_device_detail(device_id) or {}
    panel_ref = device_panel_href(detail.get("bad_id"), device_id)
    if not db.set_device_archived(device_id, False):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(url=f"{panel_ref}?view=admin", status_code=303)


@router.post("/devices/{device_id}/delete")
def device_delete(
    device_id: str,
    confirm: str = Form(""),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return RedirectResponse(url="/devices", status_code=303)
    device_id = canonical
    detail = db.get_device_detail(device_id) or {}
    panel_ref = device_panel_href(detail.get("bad_id"), device_id)
    if (confirm or "").strip() != device_id:
        return RedirectResponse(
            url=f"{panel_ref}?delete_error=1", status_code=303
        )
    db.delete_device(device_id)
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
        return _html(
            request,
            "device_missing.html",
            {"device_id": survivor_id, "user": user},
            status_code=404,
        )
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
    survivor_canonical = resolve_device_ref(db, (survivor_id or "").strip())
    if not survivor_canonical:
        return _html(
            request,
            "device_missing.html",
            {"device_id": survivor_id, "user": user},
            status_code=404,
        )
    survivor_id = survivor_canonical
    donor = (donor_id or "").strip()
    donor_resolved = resolve_device_ref(db, (donor or "").strip()) if donor else None
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


@router.post("/devices/{device_id}/tags")
def device_tags_save(
    device_id: str,
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    tags: str = Form(""),
):
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    device_id = canonical
    try:
        db.set_device_tags(device_id, tags)
    except KeyError:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    ctx = _device_config_context(
        db,
        device_id,
        user=user,
        settings=settings,
        message="Теги сохранены",
        active_view="admin",
    )
    assert ctx is not None
    return _html(request, "device_detail.html", ctx)


@router.post("/devices/{device_id}/config-override")
def device_config_override_save(
    device_id: str,
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
    canonical = resolve_device_ref(db, (device_id or "").strip())
    if not canonical:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    device_id = canonical
    if clear_override is not None:
        if not db.get_device_detail(device_id):
            return _html(
                request,
                "device_missing.html",
                {"device_id": device_id, "user": user},
                status_code=404,
            )
        db.delete_device_config_override(device_id)
        ctx = _device_config_context(
            db,
            device_id,
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
            device_id,
            user=user,
            settings=settings,
            error="Укажите хотя бы одно поле ручной настройки (или очистите)",
            active_view="config",
        )
        if not ctx:
            return _html(
                request,
                "device_missing.html",
                {"device_id": device_id, "user": user},
                status_code=404,
            )
        return _html(
            request, "device_detail.html", ctx, status_code=400
        )
    pin_err = _validate_update_target_pin(db, cleaned)
    if pin_err:
        ctx = _device_config_context(
            db,
            device_id,
            user=user,
            settings=settings,
            error=pin_err,
            active_view="config",
        )
        assert ctx is not None
        return _html(request, "device_detail.html", ctx, status_code=400)
    try:
        db.set_device_config_override(device_id, cleaned)
    except KeyError:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    ctx = _device_config_context(
        db,
        device_id,
        user=user,
        settings=settings,
        message="Ручное переопределение сохранено",
        active_view="config",
    )
    assert ctx is not None
    return _html(request, "device_detail.html", ctx)


@router.get("/account/password", response_class=HTMLResponse)
def password_page(
    request: Request,
    user: WebUser = Depends(require_web_user),
):
    if user.source != "local":
        return RedirectResponse(url="/", status_code=303)
    return _html(
        request,
        "password.html",
        {
            "user": user,
            "message": None,
            "error": None,
            "forced": user.must_change_password,
        },
    )


@router.post("/account/password")
def password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    session_secret: str = Depends(get_session_secret),
):
    if user.source != "local":
        return RedirectResponse(url="/", status_code=303)

    def render(error: str, status_code: int = 400):
        return _html(
            request,
            "password.html",
            {
                "user": user,
                "message": None,
                "error": error,
                "forced": user.must_change_password,
            },
            status_code=status_code,
        )

    if len(new_password) < 8:
        return render("Новый пароль — не короче 8 символов")
    if new_password != new_password_confirm:
        return render("Подтверждение пароля не совпадает")
    if new_password == "admin":
        return render("Выберите пароль, отличный от значения по умолчанию")

    row = db.get_local_user(user.username)
    if not row or not verify_secret(row["password_hash"], current_password):
        return render("Текущий пароль неверен", status_code=401)

    db.update_local_user_password(user.username, hash_secret(new_password), clear_must_change=True)
    updated = WebUser(
        username=user.username,
        role=user.role,
        source="local",
        must_change_password=False,
        display_name=user.display_name,
    )
    resp = RedirectResponse(url="/", status_code=303)
    settings = get_settings()
    _set_session_cookie(
        resp, session_secret, updated, request=request, settings=settings
    )
    return resp


def _ldap_form_context(
    row: dict,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    test_result: Optional[str] = None,
) -> dict:
    has_bind_password = bool(row.get("bind_password_enc"))
    return {
        "user": user,
        "settings_section": "ldap",
        "message": message,
        "error": error,
        "test_result": test_result,
        "has_bind_password": has_bind_password,
        "ldap": {
            "enabled": bool(row.get("enabled")),
            "host": row.get("host") or "",
            "port": int(row.get("port") or 389),
            "use_ssl": bool(row.get("use_ssl")),
            "start_tls": bool(row.get("start_tls")),
            "bind_dn": row.get("bind_dn") or "",
            "user_search_base": row.get("user_search_base") or "",
            "user_filter_template": row.get("user_filter_template")
            or "(uid={username})",
            "display_name_attr": row.get("display_name_attr") or "cn",
            "default_role": row.get("default_role") or "operator",
            "allowed_group": row.get("allowed_group") or "",
            "tls_insecure": bool(row.get("tls_insecure")),
        },
    }


def _parse_ldap_form(form: LdapFormData) -> tuple[dict, Optional[str]]:
    try:
        port_i = int(form.port or "389")
    except ValueError:
        return {}, "Порт должен быть целым числом"
    if port_i < 1 or port_i > 65535:
        return {}, "Порт должен быть от 1 до 65535"
    role = (form.default_role or "operator").strip().lower()
    if role not in {"admin", "operator"}:
        return {}, "Роль по умолчанию: admin или operator"
    template = (form.user_filter_template or "").strip() or "(uid={username})"
    if "{username}" not in template:
        return {}, "Шаблон фильтра должен содержать {username}"
    return {
        "enabled": form.enabled is not None,
        "host": (form.host or "").strip(),
        "port": port_i,
        "use_ssl": form.use_ssl is not None,
        "start_tls": form.start_tls is not None,
        "bind_dn": (form.bind_dn or "").strip(),
        "bind_password": form.bind_password,  # пусто = без изменений
        "user_search_base": (form.user_search_base or "").strip(),
        "user_filter_template": template,
        "display_name_attr": (form.display_name_attr or "cn").strip() or "cn",
        "default_role": role,
        "allowed_group": (form.allowed_group or "").strip(),
        "tls_insecure": form.tls_insecure is not None,
    }, None


def _apply_bool_form_fields(raw: dict, fields: dict[str, str]) -> None:
    for key, raw_val in fields.items():
        text = (raw_val or "").strip().lower()
        if text in {"true", "false", "1", "0"}:
            raw[key] = text in {"true", "1"}


def _settings_raw_from_form(
    *,
    inventory_interval_hours: str = "",
    heartbeat_interval_minutes: str = "",
    update_check_interval_hours: str = "",
    update_enabled: str = "",
    update_target: str = "",
    collect_hardware: str = "",
    collect_users: str = "",
    collect_software: str = "",
) -> dict:
    """Общий harvest interval/bool/update_target из HTML-форм (policy + device override)."""
    raw: dict = {}
    for key, raw_val in (
        ("inventory_interval_hours", inventory_interval_hours),
        ("heartbeat_interval_minutes", heartbeat_interval_minutes),
        ("update_check_interval_hours", update_check_interval_hours),
    ):
        text = (raw_val or "").strip()
        if text:
            raw[key] = text
    _apply_bool_form_fields(
        raw,
        {
            "update_enabled": update_enabled,
            "collect_hardware": collect_hardware,
            "collect_users": collect_users,
            "collect_software": collect_software,
        },
    )
    target = (update_target or "").strip()
    if target:
        raw["update_target"] = target
    return raw


def _parse_policy_form(
    *,
    name: str,
    enabled: Optional[str],
    priority: str,
    cond_field: str,
    cond_op: str,
    cond_value: str,
    inventory_interval_hours: str,
    heartbeat_interval_minutes: str,
    update_check_interval_hours: str,
    update_enabled: str,
    update_target: str = "",
    collect_hardware: str = "",
    collect_users: str = "",
    collect_software: str = "",
) -> tuple[Optional[dict], Optional[str]]:
    name_s = (name or "").strip()
    if not name_s:
        return None, "Укажите имя"
    try:
        priority_i = int((priority or "100").strip())
    except ValueError:
        return None, "Priority должен быть целым числом"
    if priority_i < 0 or priority_i > 1_000_000:
        return None, "Priority вне допустимого диапазона"

    conditions = sanitize_conditions(
        [
            {
                "field": (cond_field or "").strip(),
                "op": (cond_op or "").strip(),
                "value": (cond_value or "").strip(),
            }
        ]
    )
    if not conditions:
        return None, "Нужно одно валидное условие (hostname/domain/os_caption/tag)"

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
    settings = sanitize_settings(raw)
    if not settings:
        return None, "Задайте хотя бы одно поле settings для политики"
    return {
        "name": name_s,
        "enabled": enabled is not None,
        "priority": priority_i,
        "conditions": conditions,
        "settings": settings,
    }, None


def _validate_update_target_pin(db: Database, settings: dict) -> Optional[str]:
    """Reject pin на версию, которой нет в зеркале (контракт 0.10)."""
    target = sanitize_update_target(settings.get("update_target"))
    if not target or target == UPDATE_TARGET_LATEST:
        return None
    if not db.get_agent_msi_version(target):
        return f"Версия {target} отсутствует в каталоге установщиков — сначала загрузите её"
    return None


_CONDITION_FIELD_LABELS_RU = {
    "hostname": "hostname",
    "domain": "domain",
    "os_caption": "os_caption (подпись ОС)",
    "tag": "tag",
}


def _filter_policy_settings(settings: object) -> dict:
    """Тема C: в UI только knobs из ALLOWED_SETTING_KEYS (без server_url/секретов)."""
    if not isinstance(settings, dict):
        return {}
    return {k: v for k, v in settings.items() if k in ALLOWED_SETTING_KEYS}


def _policies_context(
    db: Database,
    user: WebUser,
    *,
    message: Optional[str] = None,
    error: Optional[str] = None,
    edit: Optional[dict] = None,
) -> dict:
    policies = []
    for p in db.list_agent_policies():
        row = dict(p)
        row["settings"] = _filter_policy_settings(row.get("settings"))
        policies.append(row)
    edit_view = edit
    if edit_view is not None:
        edit_view = dict(edit_view)
        edit_view["settings"] = _filter_policy_settings(edit_view.get("settings"))
    return {
        "user": user,
        "policies": policies,
        "defaults": dict(DEFAULT_AGENT_SETTINGS),
        "allowed_setting_keys": sorted(ALLOWED_SETTING_KEYS),
        "condition_fields": sorted(CONDITION_FIELDS),
        "condition_field_labels": _CONDITION_FIELD_LABELS_RU,
        "condition_ops": sorted(CONDITION_OPS),
        "msi_versions": db.list_agent_msi_versions(),
        "message": message,
        "error": error,
        "edit": edit_view,
    }


@router.get("/settings/policies", response_class=HTMLResponse)
def policies_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    return _html(request, "policies.html", _policies_context(db, user))


@router.get("/settings/policies/{policy_id}", response_class=HTMLResponse)
def policy_edit_page(
    policy_id: int,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    policy = db.get_agent_policy(policy_id)
    if not policy:
        return RedirectResponse(url="/settings/policies", status_code=303)
    return _html(
        request, "policies.html", _policies_context(db, user, edit=policy)
    )


@router.post("/settings/policies")
def policy_create(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    name: str = Form(""),
    enabled: Optional[str] = Form(None),
    priority: str = Form("100"),
    cond_field: str = Form("hostname"),
    cond_op: str = Form("contains"),
    cond_value: str = Form(""),
    inventory_interval_hours: str = Form(""),
    heartbeat_interval_minutes: str = Form(""),
    update_check_interval_hours: str = Form(""),
    update_enabled: str = Form(""),
    update_target: str = Form(""),
    collect_hardware: str = Form(""),
    collect_users: str = Form(""),
    collect_software: str = Form(""),
):
    parsed, err = _parse_policy_form(
        name=name,
        enabled=enabled,
        priority=priority,
        cond_field=cond_field,
        cond_op=cond_op,
        cond_value=cond_value,
        inventory_interval_hours=inventory_interval_hours,
        heartbeat_interval_minutes=heartbeat_interval_minutes,
        update_check_interval_hours=update_check_interval_hours,
        update_enabled=update_enabled,
        update_target=update_target,
        collect_hardware=collect_hardware,
        collect_users=collect_users,
        collect_software=collect_software,
    )
    if err or not parsed:
        return _html(
            request,
            "policies.html",
            _policies_context(db, user, error=err),
            status_code=400,
        )
    pin_err = _validate_update_target_pin(db, parsed["settings"])
    if pin_err:
        return _html(
            request,
            "policies.html",
            _policies_context(db, user, error=pin_err),
            status_code=400,
        )
    db.create_agent_policy(**parsed)
    return _html(
        request,
        "policies.html",
        _policies_context(db, user, message="Политика создана"),
    )


@router.post("/settings/policies/{policy_id}")
def policy_update(
    policy_id: int,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    name: str = Form(""),
    enabled: Optional[str] = Form(None),
    priority: str = Form("100"),
    cond_field: str = Form("hostname"),
    cond_op: str = Form("contains"),
    cond_value: str = Form(""),
    inventory_interval_hours: str = Form(""),
    heartbeat_interval_minutes: str = Form(""),
    update_check_interval_hours: str = Form(""),
    update_enabled: str = Form(""),
    update_target: str = Form(""),
    collect_hardware: str = Form(""),
    collect_users: str = Form(""),
    collect_software: str = Form(""),
):
    parsed, err = _parse_policy_form(
        name=name,
        enabled=enabled,
        priority=priority,
        cond_field=cond_field,
        cond_op=cond_op,
        cond_value=cond_value,
        inventory_interval_hours=inventory_interval_hours,
        heartbeat_interval_minutes=heartbeat_interval_minutes,
        update_check_interval_hours=update_check_interval_hours,
        update_enabled=update_enabled,
        update_target=update_target,
        collect_hardware=collect_hardware,
        collect_users=collect_users,
        collect_software=collect_software,
    )
    if err or not parsed:
        return _html(
            request,
            "policies.html",
            _policies_context(
                db, user, error=err, edit=db.get_agent_policy(policy_id)
            ),
            status_code=400,
        )
    pin_err = _validate_update_target_pin(db, parsed["settings"])
    if pin_err:
        return _html(
            request,
            "policies.html",
            _policies_context(
                db, user, error=pin_err, edit=db.get_agent_policy(policy_id)
            ),
            status_code=400,
        )
    updated = db.update_agent_policy(policy_id, **parsed)
    if not updated:
        return RedirectResponse(url="/settings/policies", status_code=303)
    return _html(
        request,
        "policies.html",
        _policies_context(db, user, message="Политика обновлена", edit=updated),
    )


@router.post("/settings/policies/{policy_id}/delete")
def policy_delete(
    policy_id: int,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    db.delete_agent_policy(policy_id)
    return RedirectResponse(url="/settings/policies", status_code=303)


@router.get("/settings/ldap", response_class=HTMLResponse)
def ldap_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    row = db.get_ldap_settings()
    return _html(
        request,
        "ldap_settings.html",
        _ldap_form_context(row, user=user),
    )


@router.post("/settings/ldap")
def ldap_settings_save(
    request: Request,
    form: LdapFormData = Depends(),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
    settings: Settings = Depends(get_settings),
):
    parsed, err = _parse_ldap_form(form)
    if err:
        row = db.get_ldap_settings()
        return _html(
            request,
            "ldap_settings.html",
            _ldap_form_context(row, user=user, error=err),
            status_code=400,
        )

    enc: Optional[str] = None
    if parsed["bind_password"].strip():
        if sensitive_over_http_blocked(settings):
            row = db.get_ldap_settings()
            return _html(
                request,
                "ldap_settings.html",
                _ldap_form_context(row, user=user, error=HTTP_SENSITIVE_MSG),
                status_code=403,
            )
        enc = encrypt_secret(data_key, parsed["bind_password"])

    db.update_ldap_settings(
        enabled=parsed["enabled"],
        host=parsed["host"],
        port=parsed["port"],
        use_ssl=parsed["use_ssl"],
        start_tls=parsed["start_tls"],
        bind_dn=parsed["bind_dn"],
        user_search_base=parsed["user_search_base"],
        user_filter_template=parsed["user_filter_template"],
        display_name_attr=parsed["display_name_attr"],
        default_role=parsed["default_role"],
        allowed_group=parsed["allowed_group"],
        tls_insecure=parsed["tls_insecure"],
        bind_password_enc=enc,
    )
    row = db.get_ldap_settings()
    return _html(
        request,
        "ldap_settings.html",
        _ldap_form_context(row, user=user, message="Настройки LDAP сохранены"),
    )


@router.post("/settings/ldap/test")
def ldap_settings_test(
    request: Request,
    form: LdapFormData = Depends(),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
):
    parsed, err = _parse_ldap_form(form)
    row = db.get_ldap_settings()
    if err:
        return _html(
            request,
            "ldap_settings.html",
            _ldap_form_context(row, user=user, error=err),
            status_code=400,
        )

    password = parsed["bind_password"].strip()
    if not password:
        existing = load_ldap_view(db, data_key)
        password = existing.bind_password

    # Тестовый bind даже если в форме LDAP выключен; defaults из settings_from_row.
    view = settings_from_row({**parsed, "enabled": True}, bind_password=password)
    ok, msg = test_connection(view)
    preview = dict(row)
    preview.update(
        {
            "enabled": 1 if parsed["enabled"] else 0,
            "host": parsed["host"],
            "port": parsed["port"],
            "use_ssl": 1 if parsed["use_ssl"] else 0,
            "start_tls": 1 if parsed["start_tls"] else 0,
            "bind_dn": parsed["bind_dn"],
            "user_search_base": parsed["user_search_base"],
            "user_filter_template": parsed["user_filter_template"],
            "display_name_attr": parsed["display_name_attr"],
            "default_role": parsed["default_role"],
            "allowed_group": parsed["allowed_group"],
            "tls_insecure": 1 if parsed["tls_insecure"] else 0,
        }
    )
    return _html(
        request,
        "ldap_settings.html",
        _ldap_form_context(
            preview,
            user=user,
            test_result=("ОК: " if ok else "Ошибка: ") + msg,
            error=None if ok else msg,
        ),
    )


def _tls_context(
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    warnings: Optional[list[str]] = None,
    tls_applied: bool = False,
) -> dict:
    status = tls_status()
    cert = status.get("cert") or {}
    configured = bool(status.get("configured"))
    mode = status.get("mode") or "http"
    domain = status.get("domain") or ""
    return {
        "user": user,
        "settings_section": "tls",
        "message": message,
        "error": error,
        "warnings": warnings or cert.get("warnings") or [],
        "mode": mode,
        "tls_mode": mode,
        "domain": domain,
        "tls_domain": domain,
        "https_url": status.get("https_url") or https_panel_url(domain),
        "tls_applied": tls_applied,
        "has_private_key": bool(status.get("has_private_key")),
        "cert_path": status.get("cert_path") or "",
        "cert": cert if configured else None,
        "apply": status.get("apply") or {},
    }


def _tls_html(
    request: Request,
    user: WebUser,
    *,
    status_code: int = 200,
    message: Optional[str] = None,
    error: Optional[str] = None,
    warnings: Optional[list[str]] = None,
    tls_applied: bool = False,
):
    return _html(
        request,
        "tls_settings.html",
        _tls_context(
            user=user,
            message=message,
            error=error,
            warnings=warnings,
            tls_applied=tls_applied,
        ),
        status_code=status_code,
    )


@router.get("/settings/tls", response_class=HTMLResponse)
def tls_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
):
    return _tls_html(request, user)


@router.post("/settings/tls")
async def tls_settings_upload(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    certificate: UploadFile = File(...),
    private_key: UploadFile = File(...),
    chain: Optional[UploadFile] = File(None),
):
    cert_raw = await certificate.read()
    key_raw = await private_key.read()
    chain_raw = b""
    if chain is not None and chain.filename:
        chain_raw = await chain.read()

    if not cert_raw:
        return _tls_html(
            request, user, error="Пустой файл сертификата", status_code=400
        )
    if not key_raw:
        return _tls_html(
            request, user, error="Пустой файл закрытого ключа", status_code=400
        )

    try:
        info = save_tls_materials(cert_raw, key_raw, chain_pem=chain_raw)
    except ValueError as exc:
        return _tls_html(request, user, error=str(exc), status_code=400)
    except OSError as exc:
        return _tls_html(
            request,
            user,
            error=f"Не удалось сохранить файлы для установки: {exc}",
            status_code=500,
        )

    apply = wait_for_apply(since=str(info.get("saved_at") or ""), timeout_seconds=12.0)
    warnings = list(info.get("warnings") or [])
    if apply.get("ok") is True:
        message = apply.get("message") or "Сертификат установлен"
        https_ok = apply.get("mode") == "https"
        if https_ok:
            message += ". Защищённое соединение включено — откройте панель по https-адресу и войдите снова."
        return _tls_html(
            request,
            user,
            message=message,
            warnings=warnings,
            tls_applied=https_ok,
        )
    if apply.get("ok") is False:
        return _tls_html(
            request,
            user,
            error=apply.get("message") or "Не удалось применить сертификат на сервере",
            warnings=warnings,
            status_code=502,
        )
    return _tls_html(
        request,
        user,
        message=(
            "Сертификат загружен; сервер применяет изменения. "
            "Обновите страницу через несколько секунд."
        ),
        warnings=warnings,
    )


def _smtp_form_context(
    row: dict,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    test_result: Optional[str] = None,
) -> dict:
    notify = parse_notify_flags(row.get("notify") or row.get("notify_json"))
    return {
        "user": user,
        "settings_section": "mail",
        "message": message,
        "error": error,
        "test_result": test_result,
        "has_password": bool(row.get("password_enc")),
        "notify": notify,
        "notify_labels": [(k, NOTIFY_LABELS_RU[k]) for k in DEFAULT_NOTIFY],
        "smtp": {
            "enabled": bool(row.get("enabled")),
            "host": row.get("host") or "",
            "port": int(row.get("port") or 587),
            "use_ssl": bool(row.get("use_ssl")),
            "use_starttls": bool(row.get("use_starttls")),
            "username": row.get("username") or "",
            "from_addr": row.get("from_addr") or "",
            "to_addrs": row.get("to_addrs") or "",
            "digest_interval_hours": int(row.get("digest_interval_hours") or 3),
            "digest_lookback_hours": int(row.get("digest_lookback_hours") or 3),
            "digest_window_start_hour": int(row.get("digest_window_start_hour") or 9),
            "digest_window_end_hour": int(row.get("digest_window_end_hour") or 19),
            "digest_weekdays": row.get("digest_weekdays_list")
            or parse_digest_weekdays(row.get("digest_weekdays")),
        },
        "digest_schedule_preview": digest_schedule_preview_ru(row),
        "digest_weekday_labels": [
            (0, "Пн"),
            (1, "Вт"),
            (2, "Ср"),
            (3, "Чт"),
            (4, "Пт"),
            (5, "Сб"),
            (6, "Вс"),
        ],
    }


def _parse_smtp_form(form: SmtpFormData) -> tuple[dict, Optional[str]]:
    try:
        port_i = int(form.port or "587")
    except ValueError:
        return {}, "Порт должен быть целым числом"
    if port_i < 1 or port_i > 65535:
        return {}, "Порт должен быть от 1 до 65535"
    try:
        digest_h = int((form.digest_interval_hours or "3").strip())
    except ValueError:
        return {}, "Интервал сводки должен быть целым числом часов"
    if digest_h < 1 or digest_h > 24:
        return {}, "Интервал сводки: от 1 до 24 часов"
    try:
        lookback_h = int((form.digest_lookback_hours or "3").strip())
    except ValueError:
        return {}, "Окно событий (lookback) должно быть целым числом часов"
    if lookback_h < 1 or lookback_h > 168:
        return {}, "Окно событий: от 1 до 168 часов"
    try:
        win_start = int((form.digest_window_start_hour or "9").strip())
        win_end = int((form.digest_window_end_hour or "19").strip())
    except ValueError:
        return {}, "Часы окна сводки должны быть целыми (0–24)"
    if win_start < 0 or win_start > 23:
        return {}, "Начало окна: час от 0 до 23"
    if win_end < 1 or win_end > 24:
        return {}, "Конец окна: час от 1 до 24 (не включительно)"
    if win_end <= win_start:
        return {}, "Конец окна должен быть позже начала"
    weekdays: list[int] = []
    for wd in range(7):
        if getattr(form, f"digest_wd_{wd}", None) is not None:
            weekdays.append(wd)
    if not weekdays:
        weekdays = default_digest_weekdays()
    flags = {key: False for key in DEFAULT_NOTIFY}
    notify_flags = {
        "hardware": form.notify_hardware,
        "stale": form.notify_stale,
        "online": form.notify_online,
        "disk_space": form.notify_disk_space,
        "enroll": form.notify_enroll,
        "hostname": form.notify_hostname,
        "domain": form.notify_domain,
        "pending_reboot": form.notify_pending_reboot,
    }
    for key, raw in notify_flags.items():
        if key in flags and raw is not None:
            flags[key] = True
    return {
        "enabled": form.enabled is not None,
        "host": (form.host or "").strip(),
        "port": port_i,
        "use_ssl": form.use_ssl is not None,
        "use_starttls": form.use_starttls is not None,
        "username": (form.username or "").strip(),
        "password": form.password,
        "from_addr": (form.from_addr or "").strip(),
        "to_addrs": (form.to_addrs or "").strip(),
        "digest_interval_hours": digest_h,
        "digest_lookback_hours": lookback_h,
        "digest_window_start_hour": win_start,
        "digest_window_end_hour": win_end,
        "digest_weekdays": json.dumps(weekdays, separators=(",", ":")),
        "notify_json": dump_notify_flags(flags),
    }, None


def _retention_context(
    db: Database,
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    stale_sec = effective_stale_after_seconds(db, settings)
    return {
        "user": user,
        "settings_section": "retention",
        "retention": db.get_retention_settings(),
        "stale_after_minutes": stale_sec // 60,
        "message": message,
        "error": error,
    }


def _backup_context(
    db: Database,
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    secrets = security_status(db, settings).get("secrets") or {}
    keys = backup_keys_status(
        data_key_file=settings.data_key_file,
        session_secret_file=settings.session_secret_file,
        secrets=secrets,
        last_key_escrow_at=db.get_site_secret("last_key_escrow_at"),
    )
    return {
        "user": user,
        "settings_section": "backups",
        "backup": backup_status(settings.backup_dir),
        "keys": keys,
        "last_backup_at": db.get_site_secret("last_backup_at"),
        "secrets": secrets,
        "message": message,
        "error": error,
    }


@router.get("/settings")
def settings_home(user: WebUser = Depends(require_web_admin)):
    return RedirectResponse(url="/settings/ldap", status_code=303)


@router.get("/settings/retention", response_class=HTMLResponse)
def retention_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _html(
        request,
        "retention_settings.html",
        _retention_context(db, settings, user=user),
    )


@router.post("/settings/retention")
def retention_settings_save(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    events_days: str = Form("90"),
    inventory_days: str = Form("180"),
    stale_after_minutes: str = Form("60"),
):
    try:
        ev = int((events_days or "90").strip())
        inv = int((inventory_days or "180").strip())
        stale_min = int((stale_after_minutes or "60").strip())
    except ValueError:
        return _html(
            request,
            "retention_settings.html",
            _retention_context(
                db,
                settings,
                user=user,
                error="Укажите целые числа (дни и минуты)",
            ),
            status_code=400,
        )
    if ev < 1 or inv < 1 or ev > 3650 or inv > 3650:
        return _html(
            request,
            "retention_settings.html",
            _retention_context(
                db,
                settings,
                user=user,
                error="Диапазон: от 1 до 3650 дней",
            ),
            status_code=400,
        )
    stale_sec = parse_site_stale_seconds(str(stale_min * 60))
    if stale_sec is None:
        stale_min_min = DEVICE_STALE_MIN_SECONDS // 60
        stale_min_max = DEVICE_STALE_MAX_SECONDS // 60
        return _html(
            request,
            "retention_settings.html",
            _retention_context(
                db,
                settings,
                user=user,
                error=(
                    f"Порог устаревания: от {stale_min_min} до {stale_min_max} минут"
                ),
            ),
            status_code=400,
        )
    db.update_retention_settings(events_days=ev, inventory_days=inv)
    db.set_site_secret(DEVICE_STALE_SITE_SECRET_KEY, str(stale_sec))
    _invalidate_fleet_snapshot_cache()
    return _html(
        request,
        "retention_settings.html",
        _retention_context(
            db,
            settings,
            user=user,
            message="Настройки хранения сохранены",
        ),
    )


@router.get("/settings/smtp")
def smtp_settings_redirect():
    return RedirectResponse(url="/settings/mail", status_code=303)


@router.get("/settings/mail", response_class=HTMLResponse)
def mail_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    return _html(
        request,
        "smtp_settings.html",
        _smtp_form_context(db.get_smtp_settings(), user=user),
    )


@router.post("/settings/mail")
def mail_settings_save(
    request: Request,
    form: SmtpFormData = Depends(),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
    settings: Settings = Depends(get_settings),
):
    parsed, err = _parse_smtp_form(form)
    if err:
        return _html(
            request,
            "smtp_settings.html",
            _smtp_form_context(db.get_smtp_settings(), user=user, error=err),
            status_code=400,
        )
    enc: Optional[str] = None
    if parsed["password"].strip():
        if sensitive_over_http_blocked(settings):
            return _html(
                request,
                "smtp_settings.html",
                _smtp_form_context(
                    db.get_smtp_settings(), user=user, error=HTTP_SENSITIVE_MSG
                ),
                status_code=403,
            )
        enc = encrypt_secret(data_key, parsed["password"])
    db.update_smtp_settings(
        enabled=parsed["enabled"],
        host=parsed["host"],
        port=parsed["port"],
        use_ssl=parsed["use_ssl"],
        use_starttls=parsed["use_starttls"],
        username=parsed["username"],
        from_addr=parsed["from_addr"],
        to_addrs=parsed["to_addrs"],
        notify_json=parsed["notify_json"],
        digest_interval_hours=parsed["digest_interval_hours"],
        digest_lookback_hours=parsed["digest_lookback_hours"],
        digest_window_start_hour=parsed["digest_window_start_hour"],
        digest_window_end_hour=parsed["digest_window_end_hour"],
        digest_weekdays=parsed["digest_weekdays"],
        password_enc=enc,
    )
    return _html(
        request,
        "smtp_settings.html",
        _smtp_form_context(
            db.get_smtp_settings(),
            user=user,
            message="Настройки почты сохранены",
        ),
    )


@router.post("/settings/mail/test")
def mail_settings_test(
    request: Request,
    form: SmtpFormData = Depends(),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
):
    parsed, err = _parse_smtp_form(form)
    row = db.get_smtp_settings()
    if err:
        return _html(
            request,
            "smtp_settings.html",
            _smtp_form_context(row, user=user, error=err),
            status_code=400,
        )
    pwd = parsed["password"].strip()
    if not pwd and row.get("password_enc"):
        pwd = decrypt_secret(data_key, row["password_enc"]) or ""
    recipients = parse_recipients(parsed["to_addrs"])
    if not parsed["from_addr"] or not recipients:
        return _html(
            request,
            "smtp_settings.html",
            _smtp_form_context(
                row,
                user=user,
                error="Укажите From и хотя бы одного получателя",
            ),
            status_code=400,
        )
    msg = build_hardware_email(
        device_id="test-device",
        hostname="TEST-HOST",
        events=[],
        from_addr=parsed["from_addr"],
        to_addrs=recipients,
    )
    ok, detail = send_email(
        host=parsed["host"],
        port=parsed["port"],
        username=parsed["username"],
        password=pwd,
        use_ssl=parsed["use_ssl"],
        use_starttls=parsed["use_starttls"],
        message=msg,
    )
    preview = dict(row)
    preview.update(
        {
            "enabled": 1 if parsed["enabled"] else 0,
            "host": parsed["host"],
            "port": parsed["port"],
            "use_ssl": 1 if parsed["use_ssl"] else 0,
            "use_starttls": 1 if parsed["use_starttls"] else 0,
            "username": parsed["username"],
            "from_addr": parsed["from_addr"],
            "to_addrs": parsed["to_addrs"],
            "notify_json": parsed["notify_json"],
            "digest_interval_hours": parsed["digest_interval_hours"],
            "digest_lookback_hours": parsed["digest_lookback_hours"],
            "digest_window_start_hour": parsed["digest_window_start_hour"],
            "digest_window_end_hour": parsed["digest_window_end_hour"],
            "digest_weekdays": parsed["digest_weekdays"],
        }
    )
    return _html(
        request,
        "smtp_settings.html",
        _smtp_form_context(
            preview,
            user=user,
            test_result=("ОК: " if ok else "Ошибка: ") + detail,
            error=None if ok else detail,
        ),
    )


@router.get("/settings/backups", response_class=HTMLResponse)
def backups_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _html(
        request,
        "backup_settings.html",
        _backup_context(db, settings, user=user),
    )


@router.post("/settings/backups/run")
def backups_settings_run(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    from .db import utc_now

    result = run_daily_backup(
        settings.backup_dir,
        database_url=settings.database_url,
    )
    if result.get("ok"):
        db.set_site_secret("last_backup_at", utc_now())
        db.set_site_secret("last_backup_path", result.get("path") or "")
        message = f"Бэкап записан: {result.get('name')}"
        error = None
    else:
        message = None
        error = result.get("error") or "Ошибка бэкапа"
    return _html(
        request,
        "backup_settings.html",
        _backup_context(db, settings, user=user, message=message, error=error),
        status_code=200 if result.get("ok") else 500,
    )



@router.get("/settings/backups/site-bundle")
def backups_site_bundle_download(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Скачать site bundle (DB + keys + MSI). Секреты только в файле, не в HTML."""
    if sensitive_over_http_blocked(settings):
        return _html(
            request,
            "backup_settings.html",
            _backup_context(db, settings, user=user, error=HTTP_SENSITIVE_MSG),
            status_code=403,
        )
    try:
        payload, filename = build_site_bundle(
            db=db,
            backup_dir=settings.backup_dir,
            updates_dir=settings.agent_updates_dir,
            data_key_file=settings.data_key_file,
            session_secret_file=settings.session_secret_file,
            include_msi_files=False,
        )
    except Exception as exc:  # noqa: BLE001
        return _html(
            request,
            "backup_settings.html",
            _backup_context(
                db, settings, user=user, error=f"Не удалось собрать bundle: {exc}"
            ),
            status_code=500,
        )
    return StreamingResponse(
        iter([payload]),
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )


@router.get("/settings/backups/key-escrow")
def backups_key_escrow_download(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Скачать только escrow keys (без DB). SEC-005; только после HTTPS."""
    from .db import utc_now

    if sensitive_over_http_blocked(settings):
        return _html(
            request,
            "backup_settings.html",
            _backup_context(db, settings, user=user, error=HTTP_SENSITIVE_MSG),
            status_code=403,
        )
    try:
        payload, filename = build_key_escrow_archive(
            data_key_file=settings.data_key_file,
            session_secret_file=settings.session_secret_file,
        )
    except Exception as exc:  # noqa: BLE001
        return _html(
            request,
            "backup_settings.html",
            _backup_context(
                db, settings, user=user, error=f"Не удалось собрать key escrow: {exc}"
            ),
            status_code=500,
        )
    db.set_site_secret("last_key_escrow_at", utc_now())
    return StreamingResponse(
        iter([payload]),
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )


def _enrollment_msi_name(db: Database) -> str:
    agent_update = db.get_agent_update()
    if agent_update and agent_update.get("msi_name"):
        return str(agent_update["msi_name"])
    versions = db.list_agent_msi_versions()
    if versions:
        top = versions[0]
        if top.get("msi_name"):
            return str(top["msi_name"])
        ver = (top.get("version") or "").strip()
        if ver:
            return f"bad-agent-{ver}.msi"
    return "bad-agent-X.Y.Z.msi"


def _build_enrollment_msiexec_script(
    token: str, server_url: str, msi_name: str
) -> str:
    return (
        f"msiexec /i {msi_name} `\n"
        f"  SERVERURL={server_url} `\n"
        f"  ENROLLMENTTOKEN={token} `\n"
        f"  ADDPATH=1 `\n"
        f"  /qn"
    )


def _updates_context(
    db: Database,
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    new_enrollment_token: Optional[str] = None,
) -> dict:
    enrollment_rotation = enrollment_rotation_signals(db, settings)
    enrollment_server_url: Optional[str] = None
    enrollment_msi_name: Optional[str] = None
    enrollment_msiexec_script: Optional[str] = None
    if new_enrollment_token:
        enrollment_server_url = (
            https_panel_url(read_domain_from_env()).rstrip("/")
            or "https://bad.example.com"
        )
        enrollment_msi_name = _enrollment_msi_name(db)
        enrollment_msiexec_script = _build_enrollment_msiexec_script(
            new_enrollment_token,
            enrollment_server_url,
            enrollment_msi_name,
        )
    return {
        "user": user,
        "settings_section": "updates",
        "agent_update": db.get_agent_update(),
        "msi_versions": db.list_agent_msi_versions(),
        "github_repo": settings.github_repo,
        "updates_dir": str(settings.agent_updates_dir),
        "sync_interval": settings.agent_update_sync_interval_seconds,
        "enrollment": enrollment_status(db, settings),
        "enrollment_rotation": enrollment_rotation,
        "message": message,
        "error": error,
        "new_enrollment_token": new_enrollment_token,
        "enrollment_server_url": enrollment_server_url,
        "enrollment_msi_name": enrollment_msi_name,
        "enrollment_msiexec_script": enrollment_msiexec_script,
    }


@router.get("/settings/updates", response_class=HTMLResponse)
def updates_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user),
    )


@router.post("/settings/updates/sync")
def updates_settings_sync(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        record = sync_from_github(db, settings)
        message = f"Синхронизировано: {record.get('version') if record else 'ok'}"
        error = None
    except Exception as exc:  # noqa: BLE001
        message = None
        error = f"Ошибка sync: {exc}"
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user, message=message, error=error),
        status_code=200 if message else 502,
    )


@router.post("/settings/updates/upload")
async def updates_settings_upload(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    msi: UploadFile = File(...),
    version: str = Form(""),
    sha256: str = Form(""),
    manifest: Optional[UploadFile] = File(None),
):
    raw = await msi.read()
    if not raw:
        return _html(
            request,
            "updates_settings.html",
            _updates_context(
                db, settings, user=user, error="Пустой файл установщика"
            ),
            status_code=400,
        )
    manifest_text = None
    if manifest is not None and manifest.filename:
        try:
            manifest_text = (await manifest.read()).decode("utf-8")
        except Exception:  # noqa: BLE001
            return _html(
                request,
                "updates_settings.html",
                _updates_context(
                    db, settings, user=user, error="Не удалось прочитать файл описания версии"
                ),
                status_code=400,
            )
    try:
        record = ingest_uploaded_msi(
            db,
            settings,
            raw=raw,
            filename=msi.filename or "",
            version=version,
            sha256=sha256,
            manifest_json=manifest_text,
        )
        message = f"Загружено: {record.get('version')} ({record.get('msi_name')})"
        error = None
    except Exception as exc:  # noqa: BLE001
        message = None
        error = f"Ошибка загрузки: {exc}"
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user, message=message, error=error),
        status_code=200 if message else 400,
    )


@router.post("/settings/updates/delete")
def updates_settings_delete(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    version: str = Form(...),
):
    ver = (version or "").strip()
    try:
        delete_msi_version(db, settings, ver)
        message = f"Удалена версия {ver} из каталога"
        error = None
        code = 200
    except ValueError as exc:
        message = None
        error = str(exc)
        code = 400
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user, message=message, error=error),
        status_code=code,
    )


@router.post("/settings/updates/set-latest")
def updates_settings_set_latest(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    version: str = Form(...),
):
    try:
        record = set_latest_msi_version(db, version.strip())
        message = f"Основная версия в каталоге: {record.get('version')}"
        error = None
        code = 200
    except ValueError as exc:
        message = None
        error = str(exc)
        code = 400
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user, message=message, error=error),
        status_code=code,
    )


@router.post("/settings/enrollment/rotate")
def enrollment_rotate(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    custom_token: str = Form(""),
):
    custom = (custom_token or "").strip()
    result = rotate_enrollment_token(
        db, settings, new_token=custom or None
    )
    notes = []
    if result.get("updated_site_env"):
        notes.append("настройки сервера обновлены")
    if result.get("wrote_token_file"):
        notes.append("токен записан на сервер")
    elif result.get("wrote_fallback_file"):
        notes.append("токен сохранён рядом с базой")
    note = "; ".join(notes) if notes else "сохранён в базе, перезапуск не нужен"
    return _html(
        request,
        "updates_settings.html",
        _updates_context(
            db,
            settings,
            user=user,
            message=f"Токен подключения агентов сменён ({note}). Сохраните значение — больше не показать.",
            new_enrollment_token=result["token"],
        ),
    )


@router.post("/settings/enrollment/wave-done")
def enrollment_wave_done(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Оператор: волна MSI закончена → rotation_due до следующего rotate."""
    mark_enrollment_wave_done(db)
    return _html(
        request,
        "updates_settings.html",
        _updates_context(
            db,
            settings,
            user=user,
            message="Волна отмечена. Смените токен подключения агентов (лента на Обзоре и раздел ниже).",
        ),
    )


def _server_update_context(
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    check: Optional[dict] = None,
    branches: Optional[list] = None,
) -> dict:
    panel = server_status_panel(settings)
    branch_list = branches
    if branch_list is None:
        try:
            branch_list = list_remote_branches(settings)
        except Exception:  # noqa: BLE001
            branch_list = []
    return {
        "user": user,
        "settings_section": "server_update",
        "panel": panel,
        "check": check,
        "branches": branch_list or [],
        "message": message,
        "error": error,
    }


def _server_update_page(
    request: Request,
    settings: Settings,
    user: WebUser,
    *,
    message: Optional[str] = None,
    error: Optional[str] = None,
    check: Optional[dict] = None,
    branches: Optional[list] = None,
    status_code: int = 200,
):
    return _html(
        request,
        "server_update_settings.html",
        _server_update_context(
            settings,
            user=user,
            message=message,
            error=error,
            check=check,
            branches=branches,
        ),
        status_code=status_code,
    )


def _server_update_wait_outcome(
    root: Path,
    req: dict,
    *,
    ok_default: str,
    fail_default: str,
    pending: str,
    timeout_seconds: float = 180.0,
) -> tuple[Optional[str], Optional[str], int]:
    apply = server_wait_for_apply(
        root,
        since=str(req.get("requested_at") or ""),
        timeout_seconds=timeout_seconds,
    )
    if apply.get("ok") is True:
        return apply.get("message") or ok_default, None, 200
    if apply.get("ok") is False:
        return None, apply.get("message") or fail_default, 502
    return pending, None, 200


@router.get("/settings/server-update", response_class=HTMLResponse)
def server_update_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
):
    return _server_update_page(request, settings, user)


@router.post("/settings/server-update/branch")
def server_update_set_branch(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    branch: str = Form(...),
):
    try:
        set_preferred_branch(branch, releases_dir(settings))
        message = f"Ветка обновления: {branch.strip()}"
        error = None
        code = 200
    except ValueError as exc:
        message = None
        error = str(exc)
        code = 400
    return _server_update_page(
        request, settings, user, message=message, error=error, status_code=code
    )


@router.post("/settings/server-update/check")
def server_update_check(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    branch: str = Form(""),
):
    try:
        result = server_check_updates(
            settings, branch=(branch or "").strip() or None
        )
        if result.get("error"):
            message = None
            error = result["error"]
            code = 502
        elif result.get("update_available"):
            remote = result.get("remote") or {}
            message = (
                f"Доступно обновление: {remote.get('short_sha') or remote.get('sha')}"
            )
            error = None
            code = 200
        else:
            message = "Установленная версия совпадает с HEAD ветки"
            error = None
            code = 200
    except ValueError as exc:
        result = None
        message = None
        error = str(exc)
        code = 400
    return _server_update_page(
        request,
        settings,
        user,
        message=message,
        error=error,
        check=result,
        status_code=code,
    )


@router.post("/settings/server-update/apply")
def server_update_apply(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    branch: str = Form(""),
    sha: str = Form(""),
):
    root = releases_dir(settings)
    try:
        req = server_request_apply(
            action="apply",
            branch=branch,
            sha=sha,
            directory=root,
        )
        message, error, code = _server_update_wait_outcome(
            root,
            req,
            ok_default="Обновление применено",
            fail_default="apply не удался",
            pending=(
                "Запрос отправлен; сервер устанавливает обновление. "
                "Обновите страницу через минуту."
            ),
        )
    except ValueError as exc:
        message = None
        error = str(exc)
        code = 400
    except OSError as exc:
        message = None
        error = f"Не удалось записать apply.request: {exc}"
        code = 500
    return _server_update_page(
        request, settings, user, message=message, error=error, status_code=code
    )


@router.post("/settings/server-update/rollback")
def server_update_rollback(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    slot_id: str = Form(...),
):
    root = releases_dir(settings)
    try:
        req = server_request_apply(
            action="rollback", slot_id=slot_id, directory=root
        )
        message, error, code = _server_update_wait_outcome(
            root,
            req,
            ok_default="Откат выполнен",
            fail_default="rollback не удался",
            pending="Запрос отката отправлен; дождитесь завершения на сервере.",
        )
    except ValueError as exc:
        message = None
        error = str(exc)
        code = 400
    return _server_update_page(
        request, settings, user, message=message, error=error, status_code=code
    )


@router.post("/settings/server-update/token")
def server_update_set_token(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    token: str = Form(...),
):
    root = releases_dir(settings)
    try:
        req = request_set_github_token(token, directory=root)
        apply = server_wait_for_apply(
            root, since=str(req.get("requested_at") or ""), timeout_seconds=30.0
        )
        get_settings.cache_clear()
        if apply.get("ok") is False:
            message = None
            error = apply.get("message") or "не удалось записать токен"
            code = 502
        else:
            message = "Токен для обновлений сохранён (значение больше не показывается)."
            error = None
            code = 200
    except ValueError as exc:
        message = None
        error = str(exc)
        code = 400
    return _server_update_page(
        request,
        get_settings(),
        user,
        message=message,
        error=error,
        status_code=code,
    )


@router.post("/settings/server-update/msi/trigger")
def server_update_msi_trigger(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    branch: str = Form(""),
    version: str = Form(""),
):
    try:
        meta = trigger_msi_workflow(
            settings,
            branch=(branch or "").strip() or None,
            version=version,
        )
        message = f"Запущена сборка установщика агента (ветка {meta.get('branch')})"
        error = None
        code = 200
    except Exception as exc:  # noqa: BLE001
        message = None
        error = str(exc)
        code = 502
    return _server_update_page(
        request, settings, user, message=message, error=error, status_code=code
    )


@router.post("/settings/server-update/msi/poll")
def server_update_msi_poll(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        meta = poll_msi_workflow(settings, ingest=True, db=db)
        st = meta.get("status")
        conclusion = meta.get("conclusion")
        if meta.get("ingested"):
            message = (
                f"Установщик добавлен в каталог: {meta['ingested'].get('version')} "
                f"({meta['ingested'].get('msi_name')})"
            )
            error = meta.get("error")
            code = 200 if not error else 502
        elif st == "completed" and conclusion != "success":
            message = None
            error = f"Сборка установщика завершилась с ошибкой: {conclusion}"
            code = 502
        else:
            message = f"Статус сборки установщика: {st or '—'} / {conclusion or '—'}"
            error = meta.get("error")
            code = 200
    except Exception as exc:  # noqa: BLE001
        message = None
        error = str(exc)
        code = 502
    return _server_update_page(
        request, settings, user, message=message, error=error, status_code=code
    )
