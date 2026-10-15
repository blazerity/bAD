"""Зеркалировать MSI из GitHub Release локально и отвечать на проверки обновлений агента."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from .config import Settings
from .db import Database
from .github_release import fetch_latest_release_assets, mirror_release_to_dir

logger = logging.getLogger(__name__)

_SEMVER_RE = re.compile(
    r"^\s*v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)",
    re.IGNORECASE,
)


def parse_semver(value: str) -> Optional[tuple[int, int, int]]:
    if not value:
        return None
    m = _SEMVER_RE.match(value)
    if not m:
        return None
    return int(m.group("major")), int(m.group("minor")), int(m.group("patch"))


def is_newer(candidate: str, current: str) -> bool:
    """True, если candidate — более высокий semver, чем current."""
    a = parse_semver(candidate)
    b = parse_semver(current)
    if a is None:
        return False
    if b is None:
        return True
    return a > b


def sync_from_github(db: Database, settings: Settings) -> dict[str, Any]:
    """Скачать assets последнего Release, сохранить MSI в каталог updates, записать в SQLite."""
    if not settings.github_repo:
        raise RuntimeError("BAD_GITHUB_REPO is not configured")

    # Токены в лог не писать.
    logger.info(
        "Syncing agent update from GitHub repo=%s",
        settings.github_repo,
    )
    assets = fetch_latest_release_assets(
        repo=settings.github_repo,
        token=settings.github_token or "",
        api_base=settings.github_api_base,
    )
    path = mirror_release_to_dir(
        assets,
        settings.agent_updates_dir,
        token=settings.github_token or "",
    )
    record = db.set_agent_update(
        version=assets.version,
        msi_name=assets.msi_name,
        sha256=assets.sha256,
        file_path=str(path),
        source_tag=assets.tag,
        release_url=assets.release_url,
    )
    logger.info(
        "Mirrored agent MSI version=%s sha256=%s path=%s",
        record["version"],
        record["sha256"],
        record["file_path"],
    )
    return record


def check_update(
    db: Database,
    current: str,
    download_path: str = "/v1/agent/update/msi",
) -> dict[str, Any]:
    mirrored = db.get_agent_update()
    if not mirrored:
        return {
            "update_available": False,
            "version": None,
            "sha256": None,
            "url": None,
            "current": current,
        }
    available = is_newer(mirrored["version"], current)
    return {
        "update_available": available,
        "version": mirrored["version"],
        "sha256": mirrored["sha256"],
        "url": download_path if available else None,
        "current": current,
        "msi_name": mirrored["msi_name"],
        "synced_at": mirrored.get("synced_at"),
    }
