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
router = APIRouter(tags=["web"], dependencies=[Depends(ensure_csrf)])


TEMPLATES_DIR = panel_root() / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))



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
    # Global HTTP bootstrap chrome (banner + gated settings actions).
    actual_tls = ctx.get("tls_mode") or tls_panel_mode()
    ctx["tls_mode"] = actual_tls
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
    if getattr(request.state, "drop_flash_cookie", False):
        resp.delete_cookie(FLASH_COOKIE, path="/")
    return resp



def _session_secret(request: Request) -> str:
    return str(getattr(request.app.state, "session_secret", None) or "")



def _take_flash(request: Request) -> dict[str, Any]:
    """Один GET забирает текст. Следующий F5 куки уже не видит."""
    token = request.cookies.get(FLASH_COOKIE)
    if not token:
        return {}
    request.state.drop_flash_cookie = True
    data = load_flash(_session_secret(request), token)
    return data or {}



def _see_other(request: Request, url: str, **payload: Any) -> RedirectResponse:
    resp = RedirectResponse(url=url, status_code=303)
    body = {key: value for key, value in payload.items() if value is not None}
    secret = _session_secret(request)
    if body and secret:
        resp.set_cookie(
            FLASH_COOKIE,
            dump_flash(secret, body),
            max_age=FLASH_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return resp



def _flash_check(result: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not isinstance(result, dict):
        return None
    remote = result.get("remote") if isinstance(result.get("remote"), dict) else {}
    sha = str(remote.get("sha") or "")
    return {
        "update_available": bool(result.get("update_available")),
        "error": result.get("error"),
        "remote": {
            "short_sha": remote.get("short_sha"),
            "sha": sha[:12],
            "message": str(remote.get("message") or "")[:200],
        }
        if remote
        else None,
    }



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
