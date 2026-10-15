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
    enroll_rate_limit_per_minute: int = 30
    snapshot_retention: int = 30
    known_schema_versions: frozenset[int] = frozenset({1})


@lru_cache
def get_settings() -> Settings:
    return Settings()
