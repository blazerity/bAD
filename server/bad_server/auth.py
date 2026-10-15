from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from .config import Settings, get_settings
from .crypto_util import decrypt_secret, generate_data_key, generate_session_secret
from .db import Database
from .ldap_client import (
    LdapGroupDenied,
    LdapSettingsView,
    authenticate_user,
    settings_from_row,
)
from .security import constant_time_equals, extract_bearer, hash_secret, verify_secret
from .sessions import WebUser, load_session


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_session_secret(request: Request, settings: Settings = Depends(get_settings)) -> str:
    secret = getattr(request.app.state, "session_secret", None) or settings.session_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session secret not configured",
        )
    return secret


def get_data_key(request: Request) -> str:
    key = getattr(request.app.state, "data_key", None)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data key not configured",
        )
    return key


def require_enrollment_token(
    authorization: Annotated[Optional[str], Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> str:
    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing enrollment token"
        )

    expected = settings.enrollment_token
    if expected:
        if not constant_time_equals(expected, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token"
            )
        return token

    hashed = db.get_site_secret("enrollment_token_hash")
    if hashed and verify_secret(hashed, token):
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token"
    )


def require_api_key(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Database = Depends(get_db),
):
    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key"
        )
    device = db.find_device_by_api_key(token, verify_secret)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    if device["revoked"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key revoked; re-enroll or rotate key in web UI",
        )
    return device


def admin_token_valid(token: Optional[str], settings: Settings, db: Database) -> bool:
    if not token:
        return False
    expected = settings.admin_token
    if expected:
        return constant_time_equals(expected, token)
    hashed = db.get_site_secret("admin_token_hash")
    if hashed:
        return verify_secret(hashed, token)
    return False


def require_admin_token(
    authorization: Annotated[Optional[str], Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> str:
    """Bearer-only admin API token (automation / agents). Web UI uses sessions."""
    token = extract_bearer(authorization)
    if not admin_token_valid(token, settings, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token"
        )
    return token or ""


def current_web_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    session_secret: str = Depends(get_session_secret),
) -> Optional[WebUser]:
    from .sessions import SESSION_COOKIE

    return load_session(session_secret, request.cookies.get(SESSION_COOKIE))


def require_web_user(
    user: Optional[WebUser] = Depends(current_web_user),
) -> WebUser:
    """HTML session gate: redirect to login (303) instead of JSON 401."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


def require_web_admin(user: WebUser = Depends(require_web_user)) -> WebUser:
    """HTML admin gate: redirect non-admins to /devices."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/devices"},
        )
    return user


def ensure_bootstrap_secrets(db: Database, settings: Settings) -> tuple[str, str]:
    """Ensure session + data encryption keys exist; return (session_secret, data_key)."""
    session_secret = settings.session_secret or db.get_site_secret("session_secret")
    if not session_secret:
        session_secret = generate_session_secret()
        db.set_site_secret("session_secret", session_secret)

    data_key = db.get_site_secret("data_key")
    if not data_key:
        data_key = generate_data_key()
        db.set_site_secret("data_key", data_key)

    return session_secret, data_key


def seed_default_admin(db: Database, settings: Settings) -> None:
    """Create local admin/admin only when no local users exist."""
    if db.count_local_users() > 0:
        return
    db.create_local_user(
        username=settings.default_admin_username,
        password_hash=hash_secret(settings.default_admin_password),
        role="admin",
        must_change_password=True,
    )


def load_ldap_view(db: Database, data_key: str) -> LdapSettingsView:
    row = db.get_ldap_settings()
    password = ""
    enc = row.get("bind_password_enc") or ""
    if enc:
        password = decrypt_secret(data_key, enc) or ""
    return settings_from_row(row, bind_password=password)


def try_local_login(db: Database, username: str, password: str) -> Optional[WebUser]:
    row = db.get_local_user(username)
    if not row:
        return None
    if not verify_secret(row["password_hash"], password):
        return None
    db.touch_local_user_login(row["username"])
    return WebUser(
        username=row["username"],
        role=row["role"] or "admin",
        source="local",
        must_change_password=bool(row["must_change_password"]),
    )


def try_ldap_login(
    db: Database, data_key: str, username: str, password: str
) -> tuple[Optional[WebUser], Optional[str]]:
    """Return (user, error). error is set for clear LDAP group denial."""
    view = load_ldap_view(db, data_key)
    if not view.enabled:
        return None, None
    try:
        result = authenticate_user(view, username, password)
    except LdapGroupDenied as exc:
        return None, (
            f"Нет доступа: пользователь не входит в группу AD «{exc.group}»"
        )
    if not result:
        return None, None
    role = view.default_role if view.default_role in {"admin", "operator"} else "operator"
    return (
        WebUser(
            username=result.username,
            role=role,
            source="ldap",
            must_change_password=False,
            display_name=result.display_name,
        ),
        None,
    )


def authenticate_web_user(
    db: Database, data_key: str, username: str, password: str
) -> tuple[Optional[WebUser], Optional[str]]:
    """Prefer local users; fall back to LDAP when enabled.

    Returns (user, error_message). Local break-glass admin is unchanged.
    """
    local = try_local_login(db, username, password)
    if local:
        return local, None
    return try_ldap_login(db, data_key, username, password)
