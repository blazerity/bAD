from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BAD_", extra="ignore")

    db_path: Path = Path(os.environ.get("BAD_DB_PATH", "./data/bad.db"))
    enrollment_token: str = ""
    admin_token: str = ""
    session_secret: str = ""
    enroll_rate_limit_per_minute: int = 30
    snapshot_retention: int = 30
    known_schema_versions: frozenset[int] = frozenset({1, 2})
    # Web-бейдж тишины: last_seen старше порога → stale (по умолчанию 1 ч).
    # Операторы могут поставить ~2× heartbeat (напр. 1800 при heartbeat 15 мин).
    device_stale_after_seconds: int = 3600
    # Создаётся только когда нет локальных пользователей (свежая БД / первый запуск).
    default_admin_username: str = "admin"
    default_admin_password: str = "admin"


    # Зеркало обновлений агента (GitHub Release → локальное хранилище). Агенты к GitHub не ходят.
    github_repo: str = "blazerity/bAD"
    github_token: str = ""  # опционально; нужен, если репозиторий станет private
    github_api_base: str = "https://api.github.com"
    agent_updates_dir: Path = Path(
        os.environ.get("BAD_AGENT_UPDATES_DIR", "/var/lib/bad/agent-updates")
    )
    agent_update_sync_interval_seconds: int = 3600  # 0 отключает фоновый sync
    agent_update_sync_on_startup: bool = True

    # Ежедневные бэкапы SQLite (сегодня + вчера в этом каталоге).
    backup_dir: Path = Path(
        os.environ.get("BAD_BACKUP_DIR", "/var/lib/bad/backups")
    )
    backup_interval_seconds: int = 3600  # как часто проверять; не чаще 1 раза в сутки


@lru_cache
def get_settings() -> Settings:
    return Settings()
