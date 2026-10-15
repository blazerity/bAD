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
    update_target: Optional[str] = None,
) -> dict[str, Any]:
    """Проверка обновления (0.10): update_target=latest|semver.

    Пока single-mirror (`agent_update`): pin срабатывает только если mirrored == target.
    Ответ additive: target_version / reason (контракт §3); legacy version/action сохранены.
    """
    target_norm = normalize_desired(update_target or desired)
    mirrored = db.get_agent_update()
    if not mirrored:
        return {
            "update_available": False,
            "version": None,
            "target_version": None,
            "sha256": None,
            "url": None,
            "current": current,
            "desired": target_norm,
            "update_target": target_norm,
            "action": "none",
            "reason": "no_mirror",
        }

    mirrored_ver = str(mirrored["version"])
    base = {
        "version": mirrored_ver,
        "sha256": mirrored["sha256"],
        "msi_name": mirrored["msi_name"],
        "synced_at": mirrored.get("synced_at"),
        "current": current,
        "desired": target_norm,
        "update_target": target_norm,
    }

    def _url_for(ver: str) -> str:
        sep = "&" if "?" in download_path else "?"
        if "version=" in download_path:
            return download_path
        return f"{download_path}{sep}version={ver}"

    if target_norm == "latest":
        available = is_newer(mirrored_ver, current)
        return {
            **base,
            "target_version": mirrored_ver if available else mirrored_ver,
            "update_available": available,
            "url": _url_for(mirrored_ver) if available else None,
            "action": "upgrade" if available else "none",
            "reason": "upgrade" if available else "already_on_or_newer_than_mirror",
        }

    # Pin: пакет на зеркале должен совпасть с target.
    pin = parse_semver(target_norm)
    mir = parse_semver(mirrored_ver)
    cur = parse_semver(current)
    if pin is None or mir is None or pin != mir:
        return {
            **base,
            "target_version": target_norm,
            "update_available": False,
            "url": None,
            "action": "none",
            "reason": "broken_pin" if pin is not None else "bad_target",
        }

    if cur is not None and cur == pin:
        return {
            **base,
            "target_version": target_norm,
            "update_available": False,
            "url": None,
            "action": "none",
            "reason": "same",
        }

    if cur is None or pin > cur:
        action = "upgrade"
    elif pin < cur:
        action = "downgrade"
    else:
        return {
            **base,
            "target_version": target_norm,
            "update_available": False,
            "url": None,
            "action": "none",
            "reason": "same",
        }

    return {
        **base,
        "target_version": target_norm,
        "update_available": True,
        "url": _url_for(target_norm),
        "action": action,
        "reason": action,
    }
