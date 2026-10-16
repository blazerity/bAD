from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from . import __version__
from .agent_config import (
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
from .db import Database
from .device_health import device_silence_status, health_snippet
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
from .backup import backup_status, run_daily_backup
from .enrollment_ops import enrollment_status, rotate_enrollment_token
from .http_bootstrap import HTTP_SENSITIVE_MSG, sensitive_over_http_blocked
from .site_bundle import build_site_bundle
from .tls_ops import (
    https_panel_url,
    read_domain_from_env,
    save_tls_materials,
    tls_panel_mode,
    tls_status,
    wait_for_apply,
)
from .smtp_mail import (
    DEFAULT_NOTIFY,
    NOTIFY_LABELS_RU,
    build_hardware_email,
    dump_notify_flags,
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


templates.env.filters["format_bytes"] = _format_bytes
templates.env.filters["format_os"] = _format_os

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
) -> list[dict]:
    """Пункты Speccy-навигации + краткие строки для Обзора (макс. ~2)."""
    hw = hardware_summary if isinstance(hardware_summary, dict) else None
    items: list[dict] = []

    def add(view_id: str, icon: str, title: str, lines: list[str]) -> None:
        items.append(
            {
                "id": view_id,
                "icon": icon,
                "title": title,
                "lines": [ln for ln in lines if ln][:2],
            }
        )

    if host_info:
        os_line = _format_os(host_info.get("os"))
        domain = host_info.get("domain") or host_info.get("hostname") or ""
        add(
            "os",
            "host",
            "Операционная система",
            [os_line, str(domain) if domain else ""],
        )

    if hw and hw.get("cpu"):
        cpu = hw["cpu"] if isinstance(hw["cpu"], dict) else {}
        cores = cpu.get("cores")
        logical = cpu.get("logical")
        cores_line = ""
        if cores is not None or logical is not None:
            cores_line = f"{cores or '—'} ядер / {logical or '—'} потоков"
        add(
            "cpu",
            "cpu",
            "Процессор",
            [str(cpu.get("name") or "—"), cores_line],
        )

    if hw and (
        hw.get("manufacturer")
        or hw.get("model")
        or hw.get("serial_number")
        or hw.get("bios_version")
        or hw.get("bios_manufacturer")
        or hw.get("bios_release_date")
    ):
        model_line = " · ".join(
            str(x) for x in (hw.get("manufacturer"), hw.get("model")) if x
        )
        bios = hw.get("bios_version")
        add(
            "mb",
            "model",
            "Материнская плата",
            [model_line or (hw.get("serial_number") or "—"), f"BIOS {bios}" if bios else ""],
        )

    if hw and (
        hw.get("ram_bytes") is not None
        or hw.get("ram_memory_type")
        or hw.get("ram_modules")
    ):
        ram = _format_bytes(hw.get("ram_bytes"))
        dtype = hw.get("ram_memory_type") or ""
        modules = hw.get("ram_modules") or []
        line1 = " · ".join(x for x in (ram if ram != "—" else "", str(dtype)) if x) or "—"
        line2 = f"{len(modules)} планок" if modules else ""
        add("memory", "ram", "Память", [line1, line2])

    if hw and hw.get("gpus"):
        gpus = hw["gpus"]
        first = gpus[0] if isinstance(gpus[0], dict) else {}
        name = first.get("name") or "—"
        extra = f"+{len(gpus) - 1}" if len(gpus) > 1 else (first.get("vendor") or "")
        add("gpu", "gpu", "Видео", [str(name), str(extra)])

    if hw and (hw.get("disks") or hw.get("volumes")):
        disks = hw.get("disks") or []
        volumes = hw.get("volumes") or []
        if disks and isinstance(disks[0], dict):
            d0 = disks[0]
            line1 = f"{d0.get('model') or 'диск'} · {_format_bytes(d0.get('size_bytes'))}"
        else:
            line1 = f"{len(disks)} диск(ов)" if disks else "тома"
        line2 = f"{len(volumes)} том(ов)" if volumes else (f"{len(disks)} диск(ов)" if len(disks) > 1 else "")
        add("storage", "disk", "Накопители", [line1, line2])

    if hw and hw.get("monitors"):
        mons = hw["monitors"]
        m0 = mons[0] if isinstance(mons[0], dict) else {}
        res = ""
        if m0.get("width") and m0.get("height"):
            res = f"{m0['width']}×{m0['height']}"
        add(
            "monitors",
            "monitor",
            "Мониторы",
            [str(m0.get("name") or m0.get("manufacturer") or "монитор"), res or f"{len(mons)} шт."],
        )

    if hw and hw.get("battery"):
        bat = hw["battery"] if isinstance(hw["battery"], dict) else {}
        charge = bat.get("charge_percent")
        line1 = f"{charge}%" if charge is not None else (bat.get("status") or "батарея")
        line2 = str(bat.get("status") or "") if charge is not None else ""
        add("battery", "battery", "Батарея", [str(line1), line2])

    if network_info and network_info.get("nics"):
        nics = network_info["nics"]
        n0 = nics[0] if isinstance(nics[0], dict) else {}
        ipv4 = n0.get("ipv4") or []
        ip = ipv4[0] if ipv4 else (n0.get("mac") or "")
        add(
            "network",
            "network",
            "Сеть",
            [str(n0.get("name") or "NIC"), str(ip)],
        )

    if users_info:
        add(
            "users",
            "users",
            "Пользователи",
            [
                str(users_info.get("last_interactive") or "—"),
                ", ".join(users_info.get("logged_on") or [])[:80],
            ],
        )

    if software_info is not None:
        programs = software_info.get("programs")
        if programs is None:
            line1 = "недоступно"
        else:
            line1 = f"{len(programs)} программ"
        add("software", "software", "ПО", [line1])

    if minidumps_info is not None:
        count = minidumps_info.get("count", "—")
        mem = "Memory.dmp есть" if minidumps_info.get("memory_dmp_present") else "Memory.dmp нет"
        add("minidumps", "events", "Минидампы BSOD", [f"{count} файлов", mem])

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
    # Global HTTP bootstrap chrome (banner + gated settings actions).
    if "tls_mode" not in ctx:
        ctx["tls_mode"] = tls_panel_mode()
    if "tls_domain" not in ctx:
        ctx["tls_domain"] = read_domain_from_env()
    if "https_url" not in ctx:
        ctx["https_url"] = https_panel_url(ctx.get("tls_domain") or "")
    resp = templates.TemplateResponse(request, name, ctx, status_code=status_code)
    settings = get_settings()
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


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    stats = db.overview_stats(stale_after_seconds=settings.device_stale_after_seconds)
    ops = ops_update_signals(
        db, stale_after_seconds=settings.device_stale_after_seconds
    )
    return _html(
        request,
        "overview.html",
        {
            "user": user,
            "stats": stats,
            "ops": ops,
            "stale_after_seconds": settings.device_stale_after_seconds,
        },
    )


@router.get("/overview", response_class=HTMLResponse)
def overview_alias(
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return home(request, user=user, db=db, settings=settings)


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
    client = request.client.host if request.client else "unknown"
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


def _enrich_device_row(device: dict, settings: Settings) -> dict:
    device = dict(device)
    device["silence"] = device_silence_status(
        device.get("last_seen_at"),
        stale_after_seconds=settings.device_stale_after_seconds,
    )
    return device


def _devices_query_params(
    *,
    tag: Optional[str],
    q: Optional[str],
    archive: bool,
    page: int,
) -> str:
    params: dict[str, str] = {}
    if tag:
        params["tag"] = tag
    if q:
        params["q"] = q
    if archive:
        params["archive"] = "1"
    if page > 1:
        params["page"] = str(page)
    return urlencode(params)


@router.get("/devices", response_class=HTMLResponse)
def devices_page(
    request: Request,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    archive: Optional[str] = None,
    page: int = 1,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    tag_filter = (tag or "").strip() or None
    query = (q or "").strip() or None
    show_archive = (archive or "").strip() in {"1", "true", "yes"}
    page_i = max(1, int(page or 1))
    total = db.count_devices(tag=tag_filter, archived=show_archive, q=query)
    page_size = DEVICES_PAGE_SIZE
    pages = max(1, (total + page_size - 1) // page_size)
    if page_i > pages:
        page_i = pages
    offset = (page_i - 1) * page_size
    devices = [
        _enrich_device_row(d, settings)
        for d in db.list_devices(
            tag=tag_filter,
            archived=show_archive,
            q=query,
            offset=offset,
            limit=page_size,
        )
    ]
    # Лёгкие подсказки о дубликатах для текущей страницы (в списке только hostname).
    host_counts: dict[str, int] = {}
    for d in db.list_devices(archived=None):
        hn = (d.get("hostname") or "").strip().casefold()
        if hn:
            host_counts[hn] = host_counts.get(hn, 0) + 1
    for d in devices:
        hn = (d.get("hostname") or "").strip().casefold()
        d["hostname_dup"] = bool(hn and host_counts.get(hn, 0) > 1)

    agent_update = db.get_agent_update()
    qs = _devices_query_params(
        tag=tag_filter, q=query, archive=show_archive, page=page_i
    )
    return _html(
        request,
        "devices.html",
        {
            "devices": devices,
            "user": user,
            "agent_update": agent_update,
            "github_repo": settings.github_repo,
            "tag_filter": tag_filter or "",
            "q": query or "",
            "show_archive": show_archive,
            "all_tags": db.list_all_tags(),
            "stale_after_seconds": settings.device_stale_after_seconds,
            "page": page_i,
            "pages": pages,
            "total": total,
            "page_size": page_size,
            "export_qs": qs,
        },
    )


@router.get("/devices/export.csv")
def devices_csv_export(
    tag: Optional[str] = None,
    q: Optional[str] = None,
    archive: Optional[str] = None,
    _user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    tag_filter = (tag or "").strip() or None
    query = (q or "").strip() or None
    show_archive = (archive or "").strip() in {"1", "true", "yes"}
    rows = db.devices_for_csv(
        tag=tag_filter, archived=show_archive, q=query
    )
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


@router.get("/events", response_class=HTMLResponse)
def events_page(
    request: Request,
    device_id: Optional[str] = None,
    page: int = 1,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    device_filter = (device_id or "").strip() or None
    page_i = max(1, int(page or 1))
    page_size = EVENTS_PAGE_SIZE
    total = db.count_device_events(device_id=device_filter)
    pages = max(1, (total + page_size - 1) // page_size)
    if page_i > pages:
        page_i = pages
    offset = (page_i - 1) * page_size
    events = db.list_device_events(
        device_id=device_filter, limit=page_size, offset=offset
    )
    return _html(
        request,
        "events.html",
        {
            "events": events,
            "user": user,
            "device_filter": device_filter or "",
            "devices": db.list_devices(archived=None),
            "page": page_i,
            "pages": pages,
            "total": total,
            "page_size": page_size,
        },
    )


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
            errs = payload.get("collector_errors")
            if isinstance(errs, list):
                collector_errors = errs
    silence = device_silence_status(
        detail.get("last_seen_at"),
        stale_after_seconds=settings.device_stale_after_seconds,
    )
    recent_events = db.list_device_events(device_id=device_id, limit=20)
    duplicates = db.find_duplicate_devices(device_id)
    inventory_nav = _device_inventory_nav(
        host_info=host_info,
        hardware_summary=hardware_summary,
        network_info=network_info,
        users_info=users_info,
        software_info=software_info,
        minidumps_info=minidumps_info,
        collector_errors=collector_errors,
    )
    inventory_ids = {item["id"] for item in inventory_nav}
    view = (active_view or "").strip()
    if view not in DEVICE_FIXED_VIEWS and view not in inventory_ids:
        view = "overview"
    return {
        "device": detail,
        "inventory_pretty": inventory_pretty,
        "hardware_summary": hardware_summary,
        "host_info": host_info,
        "network_info": network_info,
        "users_info": users_info,
        "software_info": software_info,
        "minidumps_info": minidumps_info,
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
        "silence": silence,
        "health_snippet": health_snippet(detail.get("meta")),
        "recent_events": recent_events,
        "tags_text": ", ".join(detail.get("tags") or []),
        "duplicates": duplicates,
        "new_api_key": None,
        "msi_versions": db.list_agent_msi_versions(),
    }


@router.get("/devices/{device_id}", response_class=HTMLResponse)
def device_detail_page(
    device_id: str,
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    view: Optional[str] = None,
):
    ctx = _device_config_context(
        db, device_id, user=user, settings=settings, active_view=view
    )
    if not ctx:
        return _html(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    return _html(request, "device_detail.html", ctx)


@router.post("/devices/{device_id}/revoke")
def device_revoke(
    device_id: str,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
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
        message="Доступ отозван: агент получит 403 до повторной регистрации или выпуска нового ключа",
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
        message="Выпущен новый API-ключ. Сохраните его — повторно показать нельзя.",
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
    if not db.set_device_archived(device_id, True):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(url=f"/devices/{device_id}?view=admin", status_code=303)


@router.post("/devices/{device_id}/restore")
def device_restore(
    device_id: str,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    if not db.set_device_archived(device_id, False):
        return RedirectResponse(url="/devices", status_code=303)
    return RedirectResponse(url=f"/devices/{device_id}?view=admin", status_code=303)


@router.post("/devices/{device_id}/delete")
def device_delete(
    device_id: str,
    confirm: str = Form(""),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    if (confirm or "").strip() != device_id:
        return RedirectResponse(
            url=f"/devices/{device_id}?delete_error=1", status_code=303
        )
    db.delete_device(device_id)
    return RedirectResponse(url="/devices", status_code=303)


@router.post("/devices/{device_id}/tags")
def device_tags_save(
    device_id: str,
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    tags: str = Form(""),
):
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
            error="Укажите хотя бы одно поле override (или очистите)",
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
        return f"update_target={target} нет в зеркале MSI — сначала загрузите версию"
    return None


def _policies_context(
    db: Database,
    user: WebUser,
    *,
    message: Optional[str] = None,
    error: Optional[str] = None,
    edit: Optional[dict] = None,
) -> dict:
    return {
        "user": user,
        "policies": db.list_agent_policies(),
        "defaults": dict(DEFAULT_AGENT_SETTINGS),
        "condition_fields": sorted(CONDITION_FIELDS),
        "condition_ops": sorted(CONDITION_OPS),
        "msi_versions": db.list_agent_msi_versions(),
        "message": message,
        "error": error,
        "edit": edit,
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
            request, user, error="Пустой файл private key", status_code=400
        )

    try:
        info = save_tls_materials(cert_raw, key_raw, chain_pem=chain_raw)
    except ValueError as exc:
        return _tls_html(request, user, error=str(exc), status_code=400)
    except OSError as exc:
        return _tls_html(
            request,
            user,
            error=f"Не удалось записать staging: {exc}",
            status_code=500,
        )

    apply = wait_for_apply(since=str(info.get("saved_at") or ""), timeout_seconds=12.0)
    warnings = list(info.get("warnings") or [])
    if apply.get("ok") is True:
        message = apply.get("message") or "Сертификат установлен"
        https_ok = apply.get("mode") == "https"
        if https_ok:
            message += ". HTTPS активен — откройте панель по HTTPS и войдите снова."
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
            error=apply.get("message") or "nginx apply не удался",
            warnings=warnings,
            status_code=502,
        )
    return _tls_html(
        request,
        user,
        message=(
            "Материалы в staging; ожидание apply "
            "(systemd bad-tls-apply.path). Обновите страницу через несколько секунд."
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
        },
    }


def _parse_smtp_form(form: SmtpFormData) -> tuple[dict, Optional[str]]:
    try:
        port_i = int(form.port or "587")
    except ValueError:
        return {}, "Порт должен быть целым числом"
    if port_i < 1 or port_i > 65535:
        return {}, "Порт должен быть от 1 до 65535"
    flags = {key: False for key in DEFAULT_NOTIFY}
    notify_flags = {
        "hardware": form.notify_hardware,
        "stale": form.notify_stale,
        "enroll": form.notify_enroll,
        "hostname": form.notify_hostname,
        "domain": form.notify_domain,
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
        "notify_json": dump_notify_flags(flags),
    }, None


def _retention_context(
    db: Database,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    return {
        "user": user,
        "settings_section": "retention",
        "retention": db.get_retention_settings(),
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
    return {
        "user": user,
        "settings_section": "backups",
        "backup": backup_status(settings.backup_dir),
        "last_backup_at": db.get_site_secret("last_backup_at"),
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
):
    return _html(
        request,
        "retention_settings.html",
        _retention_context(db, user=user),
    )


@router.post("/settings/retention")
def retention_settings_save(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    events_days: str = Form("90"),
    inventory_days: str = Form("180"),
):
    try:
        ev = int((events_days or "90").strip())
        inv = int((inventory_days or "180").strip())
    except ValueError:
        return _html(
            request,
            "retention_settings.html",
            _retention_context(db, user=user, error="Укажите целые числа дней"),
            status_code=400,
        )
    if ev < 1 or inv < 1 or ev > 3650 or inv > 3650:
        return _html(
            request,
            "retention_settings.html",
            _retention_context(
                db, user=user, error="Диапазон: от 1 до 3650 дней"
            ),
            status_code=400,
        )
    db.update_retention_settings(events_days=ev, inventory_days=inv)
    return _html(
        request,
        "retention_settings.html",
        _retention_context(
            db, user=user, message="Настройки хранения сохранены"
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
        events=[
            {
                "type": "cpu_change",
                "summary": "Тестовое письмо SMTP из панели bAD",
            }
        ],
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

    result = run_daily_backup(settings.db_path, settings.backup_dir)
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
            db_path=settings.db_path,
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


def _updates_context(
    db: Database,
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    new_enrollment_token: Optional[str] = None,
) -> dict:
    return {
        "user": user,
        "settings_section": "updates",
        "agent_update": db.get_agent_update(),
        "msi_versions": db.list_agent_msi_versions(),
        "github_repo": settings.github_repo,
        "updates_dir": str(settings.agent_updates_dir),
        "sync_interval": settings.agent_update_sync_interval_seconds,
        "enrollment": enrollment_status(db, settings),
        "message": message,
        "error": error,
        "new_enrollment_token": new_enrollment_token,
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
                db, settings, user=user, error="Пустой файл MSI"
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
                    db, settings, user=user, error="Не удалось прочитать manifest"
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
        message = f"Latest → {record.get('version')}"
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
        notes.append("site.env обновлён")
    if result.get("wrote_token_file"):
        notes.append(f"файл {result.get('token_file')}")
    elif result.get("wrote_fallback_file"):
        notes.append("файл рядом с БД")
    note = "; ".join(notes) if notes else "только hash в SQLite (restart не нужен)"
    return _html(
        request,
        "updates_settings.html",
        _updates_context(
            db,
            settings,
            user=user,
            message=f"Enrollment token сменён ({note}). Сохраните значение — больше не показать.",
            new_enrollment_token=result["token"],
        ),
    )
