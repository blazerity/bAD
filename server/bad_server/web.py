from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import __version__
from .agent_config import (
    CONDITION_FIELDS,
    CONDITION_OPS,
    DEFAULT_AGENT_SETTINGS,
    sanitize_conditions,
    sanitize_settings,
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
from .crypto_util import encrypt_secret
from .db import Database
from .device_health import (
    device_silence_status,
    health_snippet,
    normalize_tags,
)
from .ldap_client import settings_from_row, test_connection
from .security import hash_secret, verify_secret
from .sessions import SESSION_COOKIE, SESSION_MAX_AGE, WebUser, dump_session

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["app_version"] = __version__

router = APIRouter(tags=["web"])


def _set_session_cookie(resp: RedirectResponse, secret: str, user: WebUser) -> None:
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=dump_session(secret, user),
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        path="/",
    )


def _clear_session_cookie(resp: RedirectResponse) -> None:
    resp.delete_cookie(SESSION_COOKIE, path="/")


class LdapFormData:
    """Shared Form fields for LDAP save/test POSTs."""

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


@router.get("/", response_class=HTMLResponse)
def home(_user: WebUser = Depends(require_web_user)):
    return RedirectResponse(url="/devices", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    user: Optional[WebUser] = Depends(current_web_user),
    db: Database = Depends(get_db),
):
    if user:
        return RedirectResponse(url="/devices", status_code=303)
    ldap = db.get_ldap_settings()
    return templates.TemplateResponse(
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
):
    user = authenticate_web_user(db, data_key, username.strip(), password)
    ldap = db.get_ldap_settings()
    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Invalid username or password",
                "ldap_enabled": bool(ldap.get("enabled")),
                "user": None,
            },
            status_code=401,
        )
    dest = "/account/password" if user.must_change_password else "/devices"
    resp = RedirectResponse(url=dest, status_code=303)
    _set_session_cookie(resp, session_secret, user)
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    _clear_session_cookie(resp)
    return resp


def _enrich_device_row(device: dict, settings: Settings) -> dict:
    silence = device_silence_status(
        device.get("last_seen_at"),
        stale_after_seconds=settings.device_stale_after_seconds,
    )
    device = dict(device)
    device["silence"] = silence
    device["health_snippet"] = health_snippet(device.get("meta"))
    return device


@router.get("/devices", response_class=HTMLResponse)
def devices_page(
    request: Request,
    tag: Optional[str] = None,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    tag_filter = (tag or "").strip() or None
    devices = [
        _enrich_device_row(d, settings) for d in db.list_devices(tag=tag_filter)
    ]
    agent_update = db.get_agent_update()
    return templates.TemplateResponse(
        request,
        "devices.html",
        {
            "devices": devices,
            "user": user,
            "agent_update": agent_update,
            "github_repo": settings.github_repo,
            "tag_filter": tag_filter or "",
            "all_tags": db.list_all_tags(),
            "stale_after_seconds": settings.device_stale_after_seconds,
        },
    )


@router.get("/events", response_class=HTMLResponse)
def events_page(
    request: Request,
    device_id: Optional[str] = None,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
):
    device_filter = (device_id or "").strip() or None
    events = db.list_device_events(device_id=device_filter, limit=200)
    return templates.TemplateResponse(
        request,
        "events.html",
        {
            "events": events,
            "user": user,
            "device_filter": device_filter or "",
            "devices": db.list_devices(),
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
) -> Optional[dict]:
    detail = db.get_device_detail(device_id)
    if not detail:
        return None
    effective = db.compute_device_effective_config(device_id)
    assert effective is not None
    override = effective.get("override") or {}
    override_settings = override.get("settings") if override else {}
    inventory_pretty = None
    latest = detail.get("latest_inventory")
    if latest and latest.get("payload") is not None:
        inventory_pretty = json.dumps(latest["payload"], indent=2, ensure_ascii=False)
    silence = device_silence_status(
        detail.get("last_seen_at"),
        stale_after_seconds=settings.device_stale_after_seconds,
    )
    recent_events = db.list_device_events(device_id=device_id, limit=20)
    return {
        "device": detail,
        "inventory_pretty": inventory_pretty,
        "user": user,
        "message": message,
        "error": error,
        "defaults": dict(DEFAULT_AGENT_SETTINGS),
        "effective": effective["settings"],
        "config_version": effective["version"],
        "matched_policies": effective["matched_policies"],
        "match_context": effective["context"],
        "override_settings": override_settings or {},
        "has_override": effective["has_override"],
        "silence": silence,
        "health_snippet": health_snippet(detail.get("meta")),
        "recent_events": recent_events,
        "tags_text": ", ".join(detail.get("tags") or []),
        "stale_after_seconds": settings.device_stale_after_seconds,
    }


@router.get("/devices/{device_id}", response_class=HTMLResponse)
def device_detail_page(
    device_id: str,
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    ctx = _device_config_context(db, device_id, user=user, settings=settings)
    if not ctx:
        return templates.TemplateResponse(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    return templates.TemplateResponse(request, "device_detail.html", ctx)


@router.post("/devices/{device_id}/tags")
def device_tags_save(
    device_id: str,
    request: Request,
    user: WebUser = Depends(require_web_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    tags: str = Form(""),
):
    if not db.get_device_detail(device_id):
        return templates.TemplateResponse(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    try:
        db.set_device_tags(device_id, normalize_tags(tags))
        message = "Tags saved"
        error = None
    except KeyError:
        return templates.TemplateResponse(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    except Exception as exc:  # noqa: BLE001 — surface to form
        message = None
        error = f"Could not save tags: {exc}"
    ctx = _device_config_context(
        db, device_id, user=user, settings=settings, message=message, error=error
    )
    assert ctx is not None
    return templates.TemplateResponse(request, "device_detail.html", ctx)


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
    collect_hardware: str = Form(""),
    collect_users: str = Form(""),
    collect_software: str = Form(""),
    clear_override: Optional[str] = Form(None),
):
    if clear_override is not None:
        if not db.get_device_detail(device_id):
            return templates.TemplateResponse(
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
            message="Manual override cleared",
        )
        assert ctx is not None
        return templates.TemplateResponse(request, "device_detail.html", ctx)

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

    cleaned = sanitize_settings(raw)
    if not cleaned:
        ctx = _device_config_context(
            db,
            device_id,
            user=user,
            settings=settings,
            error="Set at least one valid override field (or clear)",
        )
        if not ctx:
            return templates.TemplateResponse(
                request,
                "device_missing.html",
                {"device_id": device_id, "user": user},
                status_code=404,
            )
        return templates.TemplateResponse(
            request, "device_detail.html", ctx, status_code=400
        )
    try:
        db.set_device_config_override(device_id, cleaned)
    except KeyError:
        return templates.TemplateResponse(
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
        message="Manual override saved",
    )
    assert ctx is not None
    return templates.TemplateResponse(request, "device_detail.html", ctx)


@router.get("/account/password", response_class=HTMLResponse)
def password_page(
    request: Request,
    user: WebUser = Depends(require_web_user),
):
    if user.source != "local":
        return RedirectResponse(url="/devices", status_code=303)
    return templates.TemplateResponse(
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
        return RedirectResponse(url="/devices", status_code=303)

    def render(error: str, status_code: int = 400):
        return templates.TemplateResponse(
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
        return render("New password must be at least 8 characters")
    if new_password != new_password_confirm:
        return render("New password confirmation does not match")
    if new_password == "admin":
        return render("Choose a password other than the default")

    row = db.get_local_user(user.username)
    if not row or not verify_secret(row["password_hash"], current_password):
        return render("Current password is incorrect", status_code=401)

    db.update_local_user_password(user.username, hash_secret(new_password), clear_must_change=True)
    updated = WebUser(
        username=user.username,
        role=user.role,
        source="local",
        must_change_password=False,
        display_name=user.display_name,
    )
    resp = RedirectResponse(url="/devices", status_code=303)
    _set_session_cookie(resp, session_secret, updated)
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
        },
    }


def _parse_ldap_form(form: LdapFormData) -> tuple[dict, Optional[str]]:
    try:
        port_i = int(form.port or "389")
    except ValueError:
        return {}, "Port must be an integer"
    if port_i < 1 or port_i > 65535:
        return {}, "Port must be between 1 and 65535"
    role = (form.default_role or "operator").strip().lower()
    if role not in {"admin", "operator"}:
        return {}, "Default role must be admin or operator"
    template = (form.user_filter_template or "").strip() or "(uid={username})"
    if "{username}" not in template:
        return {}, "User filter template must contain {username}"
    return {
        "enabled": form.enabled is not None,
        "host": (form.host or "").strip(),
        "port": port_i,
        "use_ssl": form.use_ssl is not None,
        "start_tls": form.start_tls is not None,
        "bind_dn": (form.bind_dn or "").strip(),
        "bind_password": form.bind_password,  # may be empty = unchanged
        "user_search_base": (form.user_search_base or "").strip(),
        "user_filter_template": template,
        "display_name_attr": (form.display_name_attr or "cn").strip() or "cn",
        "default_role": role,
    }, None


def _apply_bool_form_fields(raw: dict, fields: dict[str, str]) -> None:
    for key, raw_val in fields.items():
        text = (raw_val or "").strip().lower()
        if text in {"true", "false", "1", "0"}:
            raw[key] = text in {"true", "1"}


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
    collect_hardware: str = "",
    collect_users: str = "",
    collect_software: str = "",
) -> tuple[Optional[dict], Optional[str]]:
    name_s = (name or "").strip()
    if not name_s:
        return None, "Name is required"
    try:
        priority_i = int((priority or "100").strip())
    except ValueError:
        return None, "Priority must be an integer"
    if priority_i < 0 or priority_i > 1_000_000:
        return None, "Priority out of range"

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
        return None, "One valid condition is required (hostname/domain/os_caption/tag)"

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
    settings = sanitize_settings(raw)
    if not settings:
        return None, "Set at least one settings field for the policy"
    return {
        "name": name_s,
        "enabled": enabled is not None,
        "priority": priority_i,
        "conditions": conditions,
        "settings": settings,
    }, None


@router.get("/settings/policies", response_class=HTMLResponse)
def policies_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    return templates.TemplateResponse(
        request,
        "policies.html",
        {
            "user": user,
            "policies": db.list_agent_policies(),
            "defaults": dict(DEFAULT_AGENT_SETTINGS),
            "condition_fields": sorted(CONDITION_FIELDS),
            "condition_ops": sorted(CONDITION_OPS),
            "message": None,
            "error": None,
            "edit": None,
        },
    )


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
    return templates.TemplateResponse(
        request,
        "policies.html",
        {
            "user": user,
            "policies": db.list_agent_policies(),
            "defaults": dict(DEFAULT_AGENT_SETTINGS),
            "condition_fields": sorted(CONDITION_FIELDS),
            "condition_ops": sorted(CONDITION_OPS),
            "message": None,
            "error": None,
            "edit": policy,
        },
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
        collect_hardware=collect_hardware,
        collect_users=collect_users,
        collect_software=collect_software,
    )
    if err or not parsed:
        return templates.TemplateResponse(
            request,
            "policies.html",
            {
                "user": user,
                "policies": db.list_agent_policies(),
                "defaults": dict(DEFAULT_AGENT_SETTINGS),
                "condition_fields": sorted(CONDITION_FIELDS),
                "condition_ops": sorted(CONDITION_OPS),
                "message": None,
                "error": err,
                "edit": None,
            },
            status_code=400,
        )
    db.create_agent_policy(**parsed)
    return templates.TemplateResponse(
        request,
        "policies.html",
        {
            "user": user,
            "policies": db.list_agent_policies(),
            "defaults": dict(DEFAULT_AGENT_SETTINGS),
            "condition_fields": sorted(CONDITION_FIELDS),
            "condition_ops": sorted(CONDITION_OPS),
            "message": "Policy created",
            "error": None,
            "edit": None,
        },
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
        collect_hardware=collect_hardware,
        collect_users=collect_users,
        collect_software=collect_software,
    )
    if err or not parsed:
        policy = db.get_agent_policy(policy_id)
        return templates.TemplateResponse(
            request,
            "policies.html",
            {
                "user": user,
                "policies": db.list_agent_policies(),
                "defaults": dict(DEFAULT_AGENT_SETTINGS),
                "condition_fields": sorted(CONDITION_FIELDS),
                "condition_ops": sorted(CONDITION_OPS),
                "message": None,
                "error": err,
                "edit": policy,
            },
            status_code=400,
        )
    updated = db.update_agent_policy(policy_id, **parsed)
    if not updated:
        return RedirectResponse(url="/settings/policies", status_code=303)
    return templates.TemplateResponse(
        request,
        "policies.html",
        {
            "user": user,
            "policies": db.list_agent_policies(),
            "defaults": dict(DEFAULT_AGENT_SETTINGS),
            "condition_fields": sorted(CONDITION_FIELDS),
            "condition_ops": sorted(CONDITION_OPS),
            "message": "Policy updated",
            "error": None,
            "edit": updated,
        },
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
    return templates.TemplateResponse(
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
):
    parsed, err = _parse_ldap_form(form)
    if err:
        row = db.get_ldap_settings()
        return templates.TemplateResponse(
            request,
            "ldap_settings.html",
            _ldap_form_context(row, user=user, error=err),
            status_code=400,
        )

    enc: Optional[str] = None
    if parsed["bind_password"].strip():
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
        bind_password_enc=enc,
    )
    row = db.get_ldap_settings()
    return templates.TemplateResponse(
        request,
        "ldap_settings.html",
        _ldap_form_context(row, user=user, message="LDAP settings saved"),
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
        return templates.TemplateResponse(
            request,
            "ldap_settings.html",
            _ldap_form_context(row, user=user, error=err),
            status_code=400,
        )

    password = parsed["bind_password"].strip()
    if not password:
        existing = load_ldap_view(db, data_key)
        password = existing.bind_password

    # Test bind even if the form leaves LDAP disabled; reuse settings_from_row defaults.
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
        }
    )
    return templates.TemplateResponse(
        request,
        "ldap_settings.html",
        _ldap_form_context(
            preview,
            user=user,
            test_result=("OK: " if ok else "Failed: ") + msg,
            error=None if ok else msg,
        ),
    )
