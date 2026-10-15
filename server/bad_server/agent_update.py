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


def normalize_desired(desired: Optional[str]) -> str:
    if not desired or not str(desired).strip():
        return "latest"
    text = str(desired).strip()
    if text.casefold() == "latest":
        return "latest"
    parsed = parse_semver(text)
    if parsed is None:
        return "latest"
    return f"{parsed[0]}.{parsed[1]}.{parsed[2]}"


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
    desired: Optional[str] = None,
) -> dict[str, Any]:
    """Проверка обновления с учётом desired=latest|semver (0.10).

    Single-mirror: pin срабатывает только если mirrored.version == desired.
    """
    desired_norm = normalize_desired(desired)
    mirrored = db.get_agent_update()
    if not mirrored:
        return {
            "update_available": False,
            "version": None,
            "sha256": None,
            "url": None,
            "current": current,
            "desired": desired_norm,
            "action": "none",
        }

    mirrored_ver = str(mirrored["version"])
    base = {
        "version": mirrored_ver,
        "sha256": mirrored["sha256"],
        "msi_name": mirrored["msi_name"],
        "synced_at": mirrored.get("synced_at"),
        "current": current,
        "desired": desired_norm,
    }

    if desired_norm == "latest":
        available = is_newer(mirrored_ver, current)
        return {
            **base,
            "update_available": available,
            "url": download_path if available else None,
            "action": "upgrade" if available else "none",
        }

    # Pin: пакет на зеркале должен совпасть с desired.
    pin = parse_semver(desired_norm)
    mir = parse_semver(mirrored_ver)
    cur = parse_semver(current)
    if pin is None or mir is None or pin != mir:
        return {
            **base,
            "update_available": False,
            "url": None,
            "action": "none",
        }

    if cur is not None and cur == pin:
        return {
            **base,
            "update_available": False,
            "url": None,
            "action": "none",
        }

    if cur is None or pin > cur:
        action = "upgrade"
    elif pin < cur:
        action = "downgrade"
    else:
        return {
            **base,
            "update_available": False,
            "url": None,
            "action": "none",
        }

    return {
        **base,
        "update_available": True,
        "url": download_path,
        "action": action,
    }
