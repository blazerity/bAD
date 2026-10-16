from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BAD_", extra="ignore")

    # Единственный runtime DB — Postgres URL (обязателен при старте API).
    database_url: str = ""
    # Каталог для lab fallback-файлов секретов (не БД).
    data_dir: Path = Path(os.environ.get("BAD_DATA_DIR", "./data"))
    enrollment_token: str = ""
    admin_token: str = ""
    # Master secrets — prefer env/file outside DB (SEC-005).
    session_secret: str = ""
    data_key: str = ""
    session_secret_file: Path = Path(
        os.environ.get("BAD_SESSION_SECRET_FILE", "/etc/bad/session_secret")
    )
    data_key_file: Path = Path(
        os.environ.get("BAD_DATA_KEY_FILE", "/etc/bad/data_key")
    )
    prefer_external_secrets: bool = _env_bool("BAD_PREFER_EXTERNAL_SECRETS", True)
    # Cookie Secure: True/False force; None = auto (X-Forwarded-Proto / HTTPS).
    # Prefer BAD_COOKIE_SECURE=auto so Secure flips with nginx without API restart.
    cookie_secure: Optional[bool] = None
    # Lab opt-out: site-bundle + LDAP/SMTP password save while mode=http.
    allow_sensitive_over_http: bool = False
    # Lab opt-out: /v1/enroll on cleartext when managed TLS is already active.
    allow_enroll_over_http: bool = False
    # После волны MSI: reminder ротации, если enrolls since rotate ≥ N (default 5).
    enrollment_rotate_after_enrolls: int = 5
    enroll_rate_limit_per_minute: int = 30
    login_rate_limit_per_minute: int = 10
    login_username_rate_limit_per_minute: int = 5
    snapshot_retention: int = 30
    known_schema_versions: frozenset[int] = frozenset({1, 2})
    # Web silence badge: last_seen older than this → stale (default 1h).
    device_stale_after_seconds: int = 3600
    # Seeded only when no local users exist (fresh DB / first boot).
    default_admin_username: str = "admin"
    default_admin_password: str = "admin"

    # Зеркало обновлений агента (GitHub Release → локальное хранилище).
    github_repo: str = "blazerity/bAD"
    github_token: str = ""
    # Опционально: файл 440 с PAT (если не в site.env). Plaintext в UI не отдаём.
    github_token_file: Path = Path(
        os.environ.get("BAD_GITHUB_TOKEN_FILE", "/etc/bad/github_token")
    )
    github_api_base: str = "https://api.github.com"
    agent_updates_dir: Path = Path(
        os.environ.get("BAD_AGENT_UPDATES_DIR", "/var/lib/bad/agent-updates")
    )
    agent_update_sync_interval_seconds: int = 3600
    agent_update_sync_on_startup: bool = True
    # Self-update панели/API (слоты ≤3 прошлых + current).
    server_releases_dir: Path = Path(
        os.environ.get("BAD_SERVER_RELEASES_DIR", "/var/lib/bad/server-releases")
    )
    # Semver агента для MSI dispatch. Пусто → agent/VERSION на диске.
    agent_package_version: str = ""

    # Ежедневные бэкапы pg_dump — сегодня + вчера.
    backup_dir: Path = Path(
        os.environ.get("BAD_BACKUP_DIR", "/var/lib/bad/backups")
    )
    backup_interval_seconds: int = 3600

    @field_validator("cookie_secure", mode="before")
    @classmethod
    def _parse_cookie_secure(cls, value):  # noqa: ANN001
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        if text in {"auto", "none"}:
            return None
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
