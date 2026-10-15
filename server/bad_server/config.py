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
    # Seeded only when no local users exist (fresh DB / first boot).
    default_admin_username: str = "admin"
    default_admin_password: str = "admin"


    # Agent update mirror (GitHub Release → local store). Agents never talk to GitHub.
    github_repo: str = "blazerity/bAD"
    github_token: str = ""  # optional; needed if the repo becomes private
    github_api_base: str = "https://api.github.com"
    agent_updates_dir: Path = Path(
        os.environ.get("BAD_AGENT_UPDATES_DIR", "/var/lib/bad/agent-updates")
    )
    agent_update_sync_interval_seconds: int = 3600  # 0 disables background sync
    agent_update_sync_on_startup: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
