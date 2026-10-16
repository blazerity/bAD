from __future__ import annotations

import logging
from pathlib import Path
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
from .security import (
    api_key_lookup,
    constant_time_equals,
    extract_bearer,
    hash_secret,
    verify_secret,
)
from .sessions import WebUser, load_session

logger = logging.getLogger(__name__)

_PASSWORD_CHANGE_PATHS = frozenset({"/account/password", "/logout"})


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

    # Prefer DB hash so UI rotate takes effect without process restart (0.10).
    hashed = db.get_site_secret("enrollment_token_hash")
    if hashed:
        if verify_secret(hashed, token):
            return token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token"
        )

    expected = settings.enrollment_token
    if expected and constant_time_equals(expected, token):
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token"
    )


def require_api_key(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    db: Database = Depends(get_db),
):
    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key"
        )
    pepper = getattr(request.app.state, "data_key", None) or ""
    lookup = api_key_lookup(pepper, token) if pepper else None
    device = db.find_device_by_api_key(token, verify_secret, lookup_hash=lookup)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    if device["revoked"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key revoked; admin must rotate key in web UI",
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
    """Только Bearer admin API token (automation). Web UI — через sessions."""
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
    request: Request,
    user: Optional[WebUser] = Depends(current_web_user),
) -> WebUser:
    """HTML-шлюз сессии: redirect на login; must_change_password → только смена пароля."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    if user.must_change_password and request.url.path not in _PASSWORD_CHANGE_PATHS:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/account/password"},
        )
    return user


def require_web_admin(user: WebUser = Depends(require_web_user)) -> WebUser:
    """HTML-шлюз admin: redirect не-админов на /devices."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/devices"},
        )
    return user


def _read_secret_file(path: Path) -> Optional[str]:
    try:
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            return text or None
    except OSError as exc:
        logger.warning("Cannot read secret file %s: %s", path, exc)
    return None


def _write_secret_file(path: Path, value: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value + "\n", encoding="utf-8")
        try:
            path.chmod(0o400)
        except OSError:
            try:
                path.chmod(0o600)
            except OSError:
                pass
        return True
    except OSError as exc:
        logger.warning("Cannot write secret file %s: %s", path, exc)
        return False


def ensure_bootstrap_secrets(db: Database, settings: Settings) -> tuple[str, str]:
    """Resolve session_secret + data_key from env/file first, DB only as legacy.

    New secrets are written outside the database when possible (SEC-005). A copy of
    ``bad.db`` / daily backups must not be treated as safe if keys still live
    only in ``site_secrets``.
    """
    env_session = (settings.session_secret or "").strip()
    env_data = (settings.data_key or "").strip()
    file_session = _read_secret_file(settings.session_secret_file) or _read_secret_file(
        settings.data_dir / ".session_secret"
    )
    file_data = _read_secret_file(settings.data_key_file) or _read_secret_file(
        settings.data_dir / ".data_key"
    )
    db_session = db.get_site_secret("session_secret")
    db_data = db.get_site_secret("data_key")

    session_secret = env_session or file_session or db_session
    data_key = env_data or file_data or db_data
    created_session = False
    created_data = False
    if not session_secret:
        session_secret = generate_session_secret()
        created_session = True
    if not data_key:
        data_key = generate_data_key()
        created_data = True

    def _persist(kind: str, value: str, path: Path, created: bool) -> None:
        if not settings.prefer_external_secrets:
            if created:
                db.set_site_secret(kind, value)
            return
        # Env already set — drop any plaintext copy from site_secrets.
        if kind == "session_secret" and env_session:
            if db.get_site_secret(kind):
                db.delete_site_secret(kind)
            return
        if kind == "data_key" and env_data:
            if db.get_site_secret(kind):
                db.delete_site_secret(kind)
            return
        if path.is_file() and _read_secret_file(path):
            if db.get_site_secret(kind):
                db.delete_site_secret(kind)
                logger.info(
                    "Removed plaintext %s from the database; using file %s", kind, path
                )
            return
        if _write_secret_file(path, value):
            if db.get_site_secret(kind):
                db.delete_site_secret(kind)
            logger.info("Stored %s outside the database at %s", kind, path)
            return
        # Dev fallback next to DB.
        fallback = settings.data_dir / f".{kind}"
        if _write_secret_file(fallback, value):
            if db.get_site_secret(kind):
                db.delete_site_secret(kind)
            logger.warning(
                "Wrote %s to %s (preferred path %s not writable)",
                kind,
                fallback,
                path,
            )
            return
        if created:
            db.set_site_secret(kind, value)
            logger.warning(
                "%s stored in the database — DB/backup copies are sensitive. "
                "Set BAD_%s or create %s (mode 0400).",
                kind,
                kind.upper(),
                path,
            )

    _persist(
        "session_secret",
        session_secret,
        settings.session_secret_file,
        created_session,
    )
    _persist(
        "data_key",
        data_key,
        settings.data_key_file,
        created_data,
    )
    if db_data and not env_data and not file_data and not settings.data_key_file.is_file():
        logger.warning(
            "data_key loaded from the database. Backups of DB dumps expose Fernet material "
            "for SMTP/LDAP passwords. Move key to BAD_DATA_KEY or %s.",
            settings.data_key_file,
        )

    return session_secret, data_key


def seed_default_admin(db: Database, settings: Settings) -> None:
    """Создать локального admin/admin только если локальных пользователей ещё нет."""
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
    """Вернуть (user, error). error задаётся при ясном отказе по группе LDAP."""
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
    """Сначала локальные пользователи; fallback на LDAP, если включён."""
    local = try_local_login(db, username, password)
    if local:
        return local, None
    return try_ldap_login(db, data_key, username, password)
