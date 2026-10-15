from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import __version__
from .auth import (
    authenticate_web_user,
    current_web_user,
    get_data_key,
    get_db,
    get_session_secret,
    load_ldap_view,
)
from .crypto_util import encrypt_secret
from .db import Database
from .ldap_client import LdapSettingsView, test_connection
from .security import hash_secret, verify_secret
from .sessions import SESSION_COOKIE, SESSION_MAX_AGE, WebUser, dump_session

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["app_version"] = __version__

router = APIRouter(tags=["web"])


def _login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)


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


@router.get("/", response_class=HTMLResponse)
def home(user: Optional[WebUser] = Depends(current_web_user)):
    if not user:
        return _login_redirect()
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


@router.get("/devices", response_class=HTMLResponse)
def devices_page(
    request: Request,
    user: Optional[WebUser] = Depends(current_web_user),
    db: Database = Depends(get_db),
):
    if not user:
        return _login_redirect()
    devices = db.list_devices()
    return templates.TemplateResponse(
        request,
        "devices.html",
        {"devices": devices, "user": user},
    )


@router.get("/devices/{device_id}", response_class=HTMLResponse)
def device_detail_page(
    device_id: str,
    request: Request,
    user: Optional[WebUser] = Depends(current_web_user),
    db: Database = Depends(get_db),
):
    if not user:
        return _login_redirect()
    detail = db.get_device_detail(device_id)
    if not detail:
        return templates.TemplateResponse(
            request,
            "device_missing.html",
            {"device_id": device_id, "user": user},
            status_code=404,
        )
    inventory_pretty = None
    latest = detail.get("latest_inventory")
    if latest and latest.get("payload") is not None:
        inventory_pretty = json.dumps(latest["payload"], indent=2, ensure_ascii=False)
    return templates.TemplateResponse(
        request,
        "device_detail.html",
        {"device": detail, "inventory_pretty": inventory_pretty, "user": user},
    )


@router.get("/account/password", response_class=HTMLResponse)
def password_page(
    request: Request,
    user: Optional[WebUser] = Depends(current_web_user),
    message: Optional[str] = None,
    error: Optional[str] = None,
):
    if not user:
        return _login_redirect()
    if user.source != "local":
        return RedirectResponse(url="/devices", status_code=303)
    return templates.TemplateResponse(
        request,
        "password.html",
        {
            "user": user,
            "message": message,
            "error": error,
            "forced": user.must_change_password,
        },
    )


@router.post("/account/password")
def password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    user: Optional[WebUser] = Depends(current_web_user),
    db: Database = Depends(get_db),
    session_secret: str = Depends(get_session_secret),
):
    if not user:
        return _login_redirect()
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


@router.get("/settings/ldap", response_class=HTMLResponse)
def ldap_settings_page(
    request: Request,
    user: Optional[WebUser] = Depends(current_web_user),
    db: Database = Depends(get_db),
):
    if not user:
        return _login_redirect()
    if not user.is_admin:
        return RedirectResponse(url="/devices", status_code=303)
    row = db.get_ldap_settings()
    return templates.TemplateResponse(
        request,
        "ldap_settings.html",
        _ldap_form_context(row, user=user),
    )


def _parse_ldap_form(
    *,
    enabled: Optional[str],
    host: str,
    port: str,
    use_ssl: Optional[str],
    start_tls: Optional[str],
    bind_dn: str,
    bind_password: str,
    user_search_base: str,
    user_filter_template: str,
    display_name_attr: str,
    default_role: str,
) -> tuple[dict, Optional[str]]:
    try:
        port_i = int(port or "389")
    except ValueError:
        return {}, "Port must be an integer"
    if port_i < 1 or port_i > 65535:
        return {}, "Port must be between 1 and 65535"
    role = (default_role or "operator").strip().lower()
    if role not in {"admin", "operator"}:
        return {}, "Default role must be admin or operator"
    template = (user_filter_template or "").strip() or "(uid={username})"
    if "{username}" not in template:
        return {}, "User filter template must contain {username}"
    return {
        "enabled": enabled is not None,
        "host": (host or "").strip(),
        "port": port_i,
        "use_ssl": use_ssl is not None,
        "start_tls": start_tls is not None,
        "bind_dn": (bind_dn or "").strip(),
        "bind_password": bind_password,  # may be empty = unchanged
        "user_search_base": (user_search_base or "").strip(),
        "user_filter_template": template,
        "display_name_attr": (display_name_attr or "cn").strip() or "cn",
        "default_role": role,
    }, None


@router.post("/settings/ldap")
def ldap_settings_save(
    request: Request,
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
    user: Optional[WebUser] = Depends(current_web_user),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
):
    if not user:
        return _login_redirect()
    if not user.is_admin:
        return RedirectResponse(url="/devices", status_code=303)

    parsed, err = _parse_ldap_form(
        enabled=enabled,
        host=host,
        port=port,
        use_ssl=use_ssl,
        start_tls=start_tls,
        bind_dn=bind_dn,
        bind_password=bind_password,
        user_search_base=user_search_base,
        user_filter_template=user_filter_template,
        display_name_attr=display_name_attr,
        default_role=default_role,
    )
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
    user: Optional[WebUser] = Depends(current_web_user),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
):
    if not user:
        return _login_redirect()
    if not user.is_admin:
        return RedirectResponse(url="/devices", status_code=303)

    parsed, err = _parse_ldap_form(
        enabled=enabled,
        host=host,
        port=port,
        use_ssl=use_ssl,
        start_tls=start_tls,
        bind_dn=bind_dn,
        bind_password=bind_password,
        user_search_base=user_search_base,
        user_filter_template=user_filter_template,
        display_name_attr=display_name_attr,
        default_role=default_role,
    )
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

    view = LdapSettingsView(
        enabled=True,
        host=parsed["host"],
        port=parsed["port"],
        use_ssl=parsed["use_ssl"],
        start_tls=parsed["start_tls"],
        bind_dn=parsed["bind_dn"],
        bind_password=password,
        user_search_base=parsed["user_search_base"],
        user_filter_template=parsed["user_filter_template"],
        display_name_attr=parsed["display_name_attr"],
        default_role=parsed["default_role"],
    )
    ok, msg = test_connection(view)
    # Re-render with form values the operator just submitted (not yet necessarily saved)
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
