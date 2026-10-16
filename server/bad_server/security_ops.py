"""Тема A: HTTPS-first + SEC-005 + enrollment rotation hooks for UI/admin."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .config import Settings
from .db import Database
from .enrollment_ops import enrollment_rotation_signals, enrollment_status
from .http_bootstrap import sensitive_over_http_blocked
from .tls_ops import tls_status


def _secret_source(
    *,
    env_value: str,
    file_path: Path,
    db_value: Optional[str],
    db_path: Path,
    kind: str,
) -> str:
    if (env_value or "").strip():
        return "env"
    if file_path.is_file() and file_path.stat().st_size > 0:
        return "file"
    fallback = db_path.parent / f".{kind}"
    if fallback.is_file() and fallback.stat().st_size > 0:
        return "fallback_file"
    if db_value:
        return "sqlite"
    return "missing"


def secrets_status(db: Database, settings: Settings) -> dict[str, Any]:
    """SEC-005: where master keys live (fresh install → file under /etc/bad)."""
    db_data = db.get_site_secret("data_key")
    db_session = db.get_site_secret("session_secret")
    data_source = _secret_source(
        env_value=settings.data_key,
        file_path=settings.data_key_file,
        db_value=db_data,
        db_path=settings.db_path,
        kind="data_key",
    )
    session_source = _secret_source(
        env_value=settings.session_secret,
        file_path=settings.session_secret_file,
        db_value=db_session,
        db_path=settings.db_path,
        kind="session_secret",
    )
    legacy = data_source == "sqlite" or session_source == "sqlite"
    return {
        "prefer_external_secrets": bool(settings.prefer_external_secrets),
        "data_key_source": data_source,
        "session_secret_source": session_source,
        "data_key_path": str(settings.data_key_file),
        "session_secret_path": str(settings.session_secret_file),
        "legacy_keys_in_sqlite": legacy,
        "ok": not legacy and data_source != "missing" and session_source != "missing",
        "hint_ru": (
            "Master keys всё ещё в SQLite — копия bad.db/backup компрометирует "
            "SMTP/LDAP и сессии. Вынесите в /etc/bad/data_key и session_secret (440)."
            if legacy
            else "Ключи вне БД (SEC-005)."
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
            "HTTP bootstrap — только доверенная сеть; агентов и длительную панель "
            "ведите по HTTPS."
            if mode != "https"
            else "HTTPS активен; агенты и панель — только TLS."
        ),
    }


def security_status(db: Database, settings: Settings) -> dict[str, Any]:
    """Сводка для UI Lead / admin API (без секретов plaintext)."""
    enrollment = enrollment_rotation_signals(db, settings)
    return {
        "https_first": https_first_status(settings),
        "secrets": secrets_status(db, settings),
        "enrollment_rotation": enrollment,
        "enrollment": enrollment_status(db, settings),
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
    out["legacy_keys_in_sqlite"] = bool(secrets.get("legacy_keys_in_sqlite"))
    out["secrets_hint"] = secrets.get("hint_ru")
    out["tls_mode"] = https.get("tls_mode") or "http"
    out["https_first_hint"] = https.get("hint_ru")
    out["security"] = security
    return out
