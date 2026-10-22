"""Тема A: HTTPS-first + SEC-005 + enrollment rotation hooks for UI/admin."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .config import Settings
from .db import Database
from .enrollment_ops import enrollment_rotation_signals
from .http_bootstrap import sensitive_over_http_blocked
from .tls_ops import tls_status

# Поля enrollment_status внутри enrollment_rotation_signals (**status).
_ENROLLMENT_STATUS_KEYS = (
    "configured",
    "has_hash",
    "rotated_at",
    "token_file",
    "token_file_exists",
    "env_bootstrap",
    "last_enrollment_at",
)


def _secret_source(
    *,
    env_value: str,
    file_path: Path,
    db_value: Optional[str],
    data_dir: Path,
    kind: str,
) -> str:
    if (env_value or "").strip():
        return "env"
    if file_path.is_file() and file_path.stat().st_size > 0:
        return "file"
    fallback = data_dir / f".{kind}"
    if fallback.is_file() and fallback.stat().st_size > 0:
        return "fallback_file"
    if db_value:
        return "db"
    return "missing"


def secrets_status(db: Database, settings: Settings) -> dict[str, Any]:
    """SEC-005: where master keys live (fresh install → file under /etc/bad)."""
    db_data = db.get_site_secret("data_key")
    db_session = db.get_site_secret("session_secret")
    data_source = _secret_source(
        env_value=settings.data_key,
        file_path=settings.data_key_file,
        db_value=db_data,
        data_dir=settings.data_dir,
        kind="data_key",
    )
    session_source = _secret_source(
        env_value=settings.session_secret,
        file_path=settings.session_secret_file,
        db_value=db_session,
        data_dir=settings.data_dir,
        kind="session_secret",
    )
    legacy = data_source == "db" or session_source == "db"
    return {
        "prefer_external_secrets": bool(settings.prefer_external_secrets),
        "data_key_source": data_source,
        "session_secret_source": session_source,
        "data_key_path": str(settings.data_key_file),
        "session_secret_path": str(settings.session_secret_file),
        "legacy_keys_in_db": legacy,
        "legacy_keys_in_sqlite": legacy,  # alias для UI до переименования шаблонов
        "ok": not legacy and data_source != "missing" and session_source != "missing",
        "hint_ru": (
            "Ключи шифрования всё ещё в базе — любая копия базы раскрывает "
            "пароли LDAP, почту и сессии. Перенесите ключи в файлы на сервере."
            if legacy
            else "Ключи хранятся вне базы — так безопаснее для резервных копий."
        ),
    }


def https_first_status(settings: Settings) -> dict[str, Any]:
    """Product contract: agents + long-lived panel on HTTPS; bootstrap temporary."""
    tls = tls_status()
    mode = (tls.get("mode") or "http").lower()
    return {
        "tls_mode": mode,
        "tls_configured": bool(tls.get("configured")),
        "domain": tls.get("domain") or "",
        "agents_require_https": True,
        "cookie_secure": (
            "auto"
            if settings.cookie_secure is None
            else ("1" if settings.cookie_secure else "0")
        ),
        "sensitive_over_http_blocked": sensitive_over_http_blocked(settings),
        "allow_sensitive_over_http": bool(settings.allow_sensitive_over_http),
        "enroll_cleartext_blocked_when_tls": not bool(settings.allow_enroll_over_http),
        "allow_enroll_over_http": bool(settings.allow_enroll_over_http),
        "hint_ru": (
            "Пока сайт без защищённого соединения — только доверенная сеть. "
            "Агентов и постоянную работу с панелью ведите по https-адресу."
            if mode != "https"
            else "Защищённое соединение включено — используйте https-адрес для панели и агентов."
        ),
    }


def security_status(db: Database, settings: Settings) -> dict[str, Any]:
    """Сводка для UI Lead / admin API (без секретов plaintext)."""
    # Один проход: rotation_signals уже включает enrollment_status.
    rotation = enrollment_rotation_signals(db, settings)
    enrollment = {k: rotation.get(k) for k in _ENROLLMENT_STATUS_KEYS}
    return {
        "https_first": https_first_status(settings),
        "secrets": secrets_status(db, settings),
        "enrollment_rotation": rotation,
        "enrollment": enrollment,
    }


def merge_security_into_ops(ops: dict[str, Any], security: dict[str, Any]) -> dict[str, Any]:
    """Flatten runbook hooks into overview ``ops`` for UI without deep template work."""
    out = dict(ops)
    er = security.get("enrollment_rotation") or {}
    secrets = security.get("secrets") or {}
    https = security.get("https_first") or {}
    out["enrollment_rotation_due"] = bool(er.get("rotation_due"))
    out["enrolled_since_rotation"] = int(er.get("enrolled_since_rotation") or 0)
    out["enrollment_rotated_at"] = er.get("rotated_at")
    out["enrollment_rotation_hint"] = er.get("hint_ru")
    out["enrollment_rotate_path"] = er.get("ui_path") or "/settings/updates"
    out["legacy_keys_in_db"] = bool(
        secrets.get("legacy_keys_in_db") or secrets.get("legacy_keys_in_sqlite")
    )
    out["legacy_keys_in_sqlite"] = out["legacy_keys_in_db"]  # alias UI
    out["secrets_hint"] = secrets.get("hint_ru")
    out["tls_mode"] = https.get("tls_mode") or "http"
    out["https_first_hint"] = https.get("hint_ru")
    out["security"] = security
    return out
